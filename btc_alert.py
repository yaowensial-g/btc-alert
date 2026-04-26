import argparse
import json
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


def get_signal(current_price, buy_price):
    change_ratio = (current_price - buy_price) / buy_price

    if change_ratio >= 0.20:
        return "sell", change_ratio
    if change_ratio <= -0.20:
        return "buy_more", change_ratio
    return "hold", change_ratio


def build_message(current_price, buy_price, change_ratio, currency, signal):
    change_percent = change_ratio * 100

    if signal == "sell":
        title = "BTC sell alert"
        content = (
            f"Current BTC price: {current_price:.2f} {currency.upper()}\n"
            f"Buy price: {buy_price:.2f} {currency.upper()}\n"
            f"Change: {change_percent:.2f}%\n"
            "Price is up at least 20%. Consider taking profit."
        )
        return title, content

    if signal == "buy_more":
        title = "BTC buy-more alert"
        content = (
            f"Current BTC price: {current_price:.2f} {currency.upper()}\n"
            f"Buy price: {buy_price:.2f} {currency.upper()}\n"
            f"Change: {change_percent:.2f}%\n"
            "Price is down at least 20%. Consider adding to your position."
        )
        return title, content

    return None, None


def check_and_notify(buy_price, currency):
    current_price = get_btc_price(currency)
    signal, change_ratio = get_signal(current_price, buy_price)

    state = load_state()
    state_key = f"{buy_price:.8f}_{currency.lower()}"
    last_signal = state.get(state_key, "hold")

    print(
        f"Current BTC price: {current_price:.2f} {currency.upper()}, "
        f"buy price: {buy_price:.2f} {currency.upper()}, "
        f"change: {change_ratio * 100:.2f}%"
    )

    if signal in {"sell", "buy_more"} and signal != last_signal:
        title, content = build_message(
            current_price=current_price,
            buy_price=buy_price,
            change_ratio=change_ratio,
            currency=currency,
            signal=signal,
        )
        success = pushplus_send(title, content)
        print("Push sent successfully." if success else "Push failed.")
        if success:
            state[state_key] = signal
            save_state(state)
        return

    if signal == "hold" and last_signal != "hold":
        state[state_key] = "hold"
        save_state(state)

    print("No new alert needed.")


def main():
    parser = argparse.ArgumentParser(
        description="Monitor BTC price and send a push alert at +/-20%."
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
