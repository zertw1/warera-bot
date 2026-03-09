import json
import logging
import httpx

logger = logging.getLogger(__name__)

# ------------------------------
# CONFIG
# ------------------------------

BASE_URL = "https://api2.warera.io/trpc"

REQUEST_TIMEOUT = 15


# ------------------------------
# GET ACTIVE BATTLES
# ------------------------------

async def get_active_battles(client):
    """Fetch active battles from WarEra API."""

    try:

        params = {
            "input": json.dumps({
                "isActive": True
            })
        }

        response = await client.get(
            f"{BASE_URL}/battle.getBattles",
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        return (
            data.get("result", {})
            .get("data", {})
            .get("items", [])
        )

    except httpx.RequestError as e:

        logger.error(f"WarEra request error: {e}")

    except Exception as e:

        logger.error(f"Error parsing active battles: {e}")

    return []


# ------------------------------
# GET LIVE BATTLE DATA (BATCHED)
# ------------------------------

async def get_live_battle_data_batched(client, battle_ids):
    """Fetch multiple live battle data in one request."""

    if not battle_ids:
        return []

    try:

        endpoints = ",".join(
            ["battle.getLiveBattleData"] * len(battle_ids)
        )

        inputs = {
            str(i): {"battleId": bid}
            for i, bid in enumerate(battle_ids)
        }

        params = {
            "batch": 1,
            "input": json.dumps(inputs)
        }

        response = await client.get(
            f"{BASE_URL}/{endpoints}",
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        batch_data = response.json()

        results = []

        for item in batch_data:

            data = (
                item.get("result", {})
                .get("data", {})
            )

            results.append(data)

        return results

    except httpx.RequestError as e:

        logger.error(f"WarEra batch request error: {e}")

    except Exception as e:

        logger.error(f"Error parsing batch battle data: {e}")

    return []


# ------------------------------
# CORE LOGIC
# ------------------------------

def check_battles_for_users(users, all_live_data, battle_states):
    """
    Check profitable battles for each user.

    Returns list of notifications.
    """

    notifications = []

    for user in users:

        user_id = user["user_id"]
        platform = user["platform"]
        threshold = user["threshold"]
        min_pool = user["min_pool"]

        for battle_id, live_data in all_live_data:

            if not live_data:
                continue

            battle_obj = live_data.get("battle")

            if not battle_obj:
                continue

            sides = [

                (
                    "Attacker",
                    battle_obj.get("attackerMoneyPer1kDamages", 0),
                    battle_obj.get("attackerMoneyPool", 0)
                ),

                (
                    "Defender",
                    battle_obj.get("defenderMoneyPer1kDamages", 0),
                    battle_obj.get("defenderMoneyPool", 0)
                )

            ]

            for side_name, ratio, pool in sides:

                if ratio < threshold or pool < min_pool:
                    continue

                state_key = (
                    user_id,
                    platform,
                    battle_id,
                    side_name
                )

                prev_state = battle_states.get(state_key)

                should_notify = False

                if prev_state is None:

                    should_notify = True

                else:

                    prev_ratio = prev_state["money_per_1k"]
                    prev_pool = prev_state["money_pool"]

                    if ratio != prev_ratio or pool > prev_pool:
                        should_notify = True

                if not should_notify:
                    continue

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
