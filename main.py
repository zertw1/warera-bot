import json
import logging
import httpx

logger = logging.getLogger(__name__)

# Base URL for the WarEra API
BASE_URL = "https://api2.warera.io/trpc"

async def get_active_battles(client):
    """Gets all active battles from the WarEra API."""
    try:
        params = {"input": json.dumps({"isActive": True})}
        response = await client.get(f"{BASE_URL}/battle.getBattles", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("result", {}).get("data", {}).get("items", [])
    except Exception as e:
        logger.error(f"Error getting active battles: {e}")
        return None

async def get_live_battle_data_batched(client, battle_ids):
    """Gets live data for multiple battles in a single batched request."""
    if not battle_ids:
        return []
    
    try:
        endpoints = ",".join(["battle.getLiveBattleData"] * len(battle_ids))
        inputs = {str(i): {"battleId": bid} for i, bid in enumerate(battle_ids)}
        params = {"batch": 1, "input": json.dumps(inputs)}
        
        response = await client.get(f"{BASE_URL}/{endpoints}", params=params)
        response.raise_for_status()
        batch_data = response.json()
        
        results = []
        for item in batch_data:
            results.append(item.get("result", {}).get("data", {}))
        return results
    except Exception as e:
        logger.error(f"Error getting batched live battle data: {e}")
        return []

def check_battles_for_users(users, all_live_data, battle_states):
    """
    Processes live battle data against a list of users.
    Args:
        users: List of user dicts.
        all_live_data: List of (battle_id, live_data) tuples.
        battle_states: Dict mapping (user_id, platform, battle_id, side) -> {money_per_1k, money_pool}
        
    Returns:
        notifications: List of notification dicts.
    """
    notifications = []
    for user in users:
        user_id = user['user_id']
        platform = user['platform']
        threshold = user['threshold']
        min_pool = user['min_pool']

        for battle_id, live_data in all_live_data:
            if not live_data: continue
            
            battle_obj = live_data.get("battle", {})
            sides = [
                ("Attacker", battle_obj.get("attackerMoneyPer1kDamages", 0), battle_obj.get("attackerMoneyPool", 0)),
                ("Defender", battle_obj.get("defenderMoneyPer1kDamages", 0), battle_obj.get("defenderMoneyPool", 0))
            ]

            for side_name, ratio, pool in sides:
                if ratio >= threshold and pool >= min_pool:
                    # Check if we already notified for this state
                    state_key = (user_id, platform, battle_id, side_name)
                    prev_state = battle_states.get(state_key)
                    
                    # Logic: Notify if first time, OR if ratio changed, OR if pool increased
                    should_notify = False
                    if prev_state is None:
                        should_notify = True
                    else:
                        if ratio != prev_state['money_per_1k'] or pool > prev_state['money_pool']:
                            should_notify = True
                    
                    if should_notify:
                        message = (
                            f"🚀 *High Profit Battle Found!* ({side_name})\n\n"
                            f"💰 Bounty: *{ratio:.2f}*/{pool}\n"
                            f"🔗 [Join Battle](https://app.warera.io/battle/{battle_id})"
                        )
                        notifications.append({
                            "user_id": user_id,
                            "platform": platform,
                            "message": message,
                            "battle_id": battle_id,
                            "side_name": side_name,
                            "ratio": ratio,
                            "pool": pool
                        })
    return notifications
