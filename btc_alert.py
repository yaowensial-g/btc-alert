import argparse
import json
import math
import time
from pathlib import Path

from get_price import get_btc_price
from push import pushplus_send


STATE_FILE = Path(__file__).with_name("btc_alert_state.json")


def load_state():
    if not STATE_FILE.exists():
        return {}

    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_percent_steps(change_ratio):
    up_step = max(0, math.floor(change_ratio * 100))
    down_step = max(0, math.floor(-change_ratio * 100))
    return up_step, down_step


def build_message(current_price, buy_price, currency, direction, percent_step):
    if direction == "up":
        title = f"BTC up {percent_step}% alert"
        content = (
            f"Current BTC price: {current_price:.2f} {currency.upper()}\n"
            f"Buy price: {buy_price:.2f} {currency.upper()}\n"
            f"Change: +{percent_step}% or more\n"
            f"BTC has reached at least {percent_step}% above your buy price."
        )
        return title, content

    title = f"BTC down {percent_step}% alert"
    content = (
        f"Current BTC price: {current_price:.2f} {currency.upper()}\n"
        f"Buy price: {buy_price:.2f} {currency.upper()}\n"
        f"Change: -{percent_step}% or more\n"
        f"BTC has reached at least {percent_step}% below your buy price."
    )
    return title, content


def send_step_alerts(current_price, buy_price, currency, direction, start_step, end_step):
    last_successful_step = start_step

    for percent_step in range(start_step + 1, end_step + 1):
        title, content = build_message(
            current_price=current_price,
            buy_price=buy_price,
            currency=currency,
            direction=direction,
            percent_step=percent_step,
        )
        success = pushplus_send(title, content)
        print(
            f"Sent {direction} {percent_step}% alert."
            if success
            else f"Failed to send {direction} {percent_step}% alert."
        )
        if not success:
            break
        last_successful_step = percent_step

    return last_successful_step


def check_and_notify(buy_price, currency):
    current_price = get_btc_price(currency)
    change_ratio = (current_price - buy_price) / buy_price
    current_change_percent = change_ratio * 100
    current_up_step, current_down_step = get_percent_steps(change_ratio)

    state = load_state()
    state_key = f"{buy_price:.8f}_{currency.lower()}"
    state_entry = state.get(state_key, {"last_up_step": 0, "last_down_step": 0})
    if not isinstance(state_entry, dict):
        state_entry = {"last_up_step": 0, "last_down_step": 0}
    last_up_step = int(state_entry.get("last_up_step", 0))
    last_down_step = int(state_entry.get("last_down_step", 0))

    print(
        f"Current BTC price: {current_price:.2f} {currency.upper()}, "
        f"buy price: {buy_price:.2f} {currency.upper()}, "
        f"change: {current_change_percent:.2f}%"
    )

    updated = False

    if current_up_step > last_up_step:
        state_entry["last_up_step"] = send_step_alerts(
            current_price=current_price,
            buy_price=buy_price,
            currency=currency,
            direction="up",
            start_step=last_up_step,
            end_step=current_up_step,
        )
        updated = state_entry["last_up_step"] != last_up_step

    if current_down_step > last_down_step:
        state_entry["last_down_step"] = send_step_alerts(
            current_price=current_price,
            buy_price=buy_price,
            currency=currency,
            direction="down",
            start_step=last_down_step,
            end_step=current_down_step,
        )
        updated = updated or state_entry["last_down_step"] != last_down_step

    if updated:
        state[state_key] = state_entry
        save_state(state)
        return

    print("No new alert needed.")


def main():
    parser = argparse.ArgumentParser(
        description="Monitor BTC price and send a push alert every 1% move from buy price."
    )
    parser.add_argument("buy_price", type=float, help="Your initial BTC buy price.")
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Check interval in seconds. Default: 300.",
    )
    parser.add_argument(
        "--currency",
        default="usd",
        help="Quote currency used by CoinGecko. Default: usd.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run only once instead of continuous monitoring.",
    )
    args = parser.parse_args()

    if args.buy_price <= 0:
        raise ValueError("buy_price must be greater than 0.")

    if args.once:
        check_and_notify(args.buy_price, args.currency)
        return

    while True:
        try:
            check_and_notify(args.buy_price, args.currency)
        except Exception as exc:
            print(f"Check failed: {exc}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
