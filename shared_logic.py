import json
import logging
import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api2.warera.io/trpc"

async def get_active_battles(client: httpx.AsyncClient):
    """Obtiene todas las batallas activas de la API de WarEra"""
    try:
        params = {"input": json.dumps({"isActive": True})}
        response = await client.get(f"{BASE_URL}/battle.getBattles", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("result", {}).get("data", {}).get("items", [])
    except Exception as e:
        logger.error(f"Error obteniendo batallas activas: {e}")
        return []

async def get_live_battle_data_batched(client: httpx.AsyncClient, battle_ids):
    """Obtiene datos en vivo de varias batallas en un request batched"""
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
        logger.error(f"Error obteniendo batallas en vivo batched: {e}")
        return []

def check_battles_for_users(users, all_live_data, battle_states):
    """
    Procesa los datos de batallas en vivo y genera notificaciones para usuarios
    """
    notifications = []
    for user in users:
        user_id = user['user_id']
        platform = user['platform']
        threshold = user['threshold']
        min_pool = user['min_pool']

        for battle_id, live_data in all_live_data:
            if not live_data: 
                continue
            
            battle_obj = live_data.get("battle", {})
            sides = [
                ("Attacker", battle_obj.get("attackerMoneyPer1kDamages", 0), battle_obj.get("attackerMoneyPool", 0)),
                ("Defender", battle_obj.get("defenderMoneyPer1kDamages", 0), battle_obj.get("defenderMoneyPool", 0))
            ]

            for side_name, ratio, pool in sides:
                if ratio >= threshold and pool >= min_pool:
                    state_key = (user_id, platform, battle_id, side_name)
                    prev_state = battle_states.get(state_key)
                    
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
