from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from kickbase_api import KickbaseApiError, KickbaseConfigurationError  # noqa: E402
import gebot_vorhersage as forecast_app  # noqa: E402


@dataclass(frozen=True, slots=True)
class AutoBidReviewItem:
    player_name: str
    player_id: str
    recent_changes: tuple[int | None, int | None, int | None]
    three_day_delta: int | None
    trigger_reason: str
    forecast: forecast_app.GebotsVorhersage
    bid_level: str
    target_bid: int
    own_offer_before: int | None
    own_offer_after: int | None
    status: str
    message: str | None = None


def main(argv: list[str] | None = None) -> int:
    parsed_argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description="Gebotsuebersicht fuer Kickbase-Marktspieler bis zum naechsten Marktwert-Update")
    parser.add_argument("--league-id", help="Liga-ID. Falls leer, wird ueber --league-name oder die erste Liga aufgeloest.")
    parser.add_argument("--league-name", help="Exakter Ligename als Alternative zur Liga-ID.")
    parser.add_argument("--token", help="Optionaler Kickbase-Token als direkter Override der Windows-Anmeldeinformationen.")
    parser.add_argument("--update-hour", type=int, default=22, help="Stunde des naechsten Marktwert-Updates in lokaler Zeit.")
    parser.add_argument("--days", type=int, default=forecast_app.DEFAULT_LOOKBACK_DAYS, help="Lookback-Fenster in Tagen.")
    parser.add_argument(
        "--value-tolerance",
        type=float,
        default=forecast_app.DEFAULT_VALUE_TOLERANCE,
        help="Marktwertband fuer Vergleichstransfers, z.B. 0.2 fuer +/-20%%.",
    )
    parser.add_argument("--safe-percentile", type=float, default=forecast_app.DEFAULT_SAFE_PERCENTILE)
    parser.add_argument("--gamble-percentile", type=float, default=forecast_app.DEFAULT_GAMBLE_PERCENTILE)
    parser.add_argument("--min-samples", type=int, default=forecast_app.DEFAULT_MIN_SAMPLES)
    parser.add_argument("--details", action="store_true", help="Zeigt je Spieler den ausfuehrlichen Detailblock an.")
    parser.add_argument(
        "--auto-bid",
        action="store_true",
        help="Setzt automatisch Gebote fuer Marktspieler bis zum naechsten Marktwert-Update, wenn sie mindestens eine der Marktwertregeln erfuellen.",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Erzwingt die reine Listenansicht ohne Auto-Gebote.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simuliert Auto-Gebote nur und sendet keine echten Offers an Kickbase.",
    )
    parser.add_argument(
        "--min-three-day-rise",
        type=int,
        default=80_000,
        help="Mindestanstieg pro Tag fuer jede der letzten 3 Marktwertaenderungen, damit automatisch geboten wird.",
    )
    parser.add_argument(
        "--min-one-day-acceleration",
        type=int,
        default=80_000,
        help="Zusaetzlicher Trigger: letzter 1T-Anstieg muss den 2T-Anstieg um mindestens diesen Wert uebertreffen.",
    )
    parser.add_argument(
        "--min-trend-reversal-rise",
        type=int,
        default=80_000,
        help="Zusaetzlicher Trigger: 2T negativ und 1T mindestens in dieser Hoehe positiv.",
    )
    parser.add_argument(
        "--min-three-day-total-rise",
        type=int,
        default=240_000,
        help="Zusaetzlicher Trigger: 1T+2T+3T muss mindestens diesen Gesamtanstieg erreichen.",
    )
    parser.add_argument(
        "--min-three-day-total-single-day-change",
        type=int,
        default=-30_000,
        help="Zusaetzlicher Trigger fuer die Summenregel: kein einzelner Tag darf unter diesem Wert liegen.",
    )
    parser.add_argument(
        "--min-step-three-day-rise",
        type=int,
        default=40_000,
        help="Zusaetzlicher Trigger Treppenregel: Mindestanstieg fuer 3T.",
    )
    parser.add_argument(
        "--min-step-two-day-rise",
        type=int,
        default=70_000,
        help="Zusaetzlicher Trigger Treppenregel: Mindestanstieg fuer 2T.",
    )
    parser.add_argument(
        "--min-step-one-day-rise",
        type=int,
        default=100_000,
        help="Zusaetzlicher Trigger Treppenregel: Mindestanstieg fuer 1T.",
    )
    parser.add_argument(
        "--min-confirmed-recovery-two-day-rise",
        type=int,
        default=50_000,
        help="Zusaetzlicher Trigger Erholung: 2T muss mindestens diesen positiven Wert erreichen.",
    )
    parser.add_argument(
        "--min-confirmed-recovery-one-day-rise",
        type=int,
        default=80_000,
        help="Zusaetzlicher Trigger Erholung: 1T muss mindestens diesen positiven Wert erreichen.",
    )
    parser.add_argument(
        "--min-confirmed-recovery-combined-rise",
        type=int,
        default=160_000,
        help="Zusaetzlicher Trigger Erholung: 1T+2T muss mindestens diesen Wert erreichen.",
    )
    parser.add_argument(
        "--max-low-price-market-value",
        type=int,
        default=3_000_000,
        help="Zusaetzlicher Trigger Billigspieler: bis zu diesem Marktwert greifen Prozent-Schwellen statt fixer Euro-Schwellen.",
    )
    parser.add_argument(
        "--min-low-price-one-day-rise-pct",
        type=float,
        default=4.0,
        help="Zusaetzlicher Trigger Billigspieler: Mindestanstieg fuer 1T in Prozent des aktuellen Marktwerts.",
    )
    parser.add_argument(
        "--min-low-price-combined-rise-pct",
        type=float,
        default=9.0,
        help="Zusaetzlicher Trigger Billigspieler: Mindestanstieg fuer 1T+2T+3T in Prozent des aktuellen Marktwerts.",
    )
    parser.add_argument(
        "--min-reacceleration-three-day-rise",
        type=int,
        default=80_000,
        help="Zusaetzlicher Trigger Re-Acceleration: 3T muss mindestens diesen Wert erreichen.",
    )
    parser.add_argument(
        "--min-reacceleration-two-day-change",
        type=int,
        default=-20_000,
        help="Zusaetzlicher Trigger Re-Acceleration: Untergrenze fuer 2T.",
    )
    parser.add_argument(
        "--max-reacceleration-two-day-change",
        type=int,
        default=30_000,
        help="Zusaetzlicher Trigger Re-Acceleration: Obergrenze fuer 2T.",
    )
    parser.add_argument(
        "--min-reacceleration-one-day-rise",
        type=int,
        default=100_000,
        help="Zusaetzlicher Trigger Re-Acceleration: 1T muss mindestens diesen Wert erreichen.",
    )
    parser.add_argument(
        "--bid-level",
        choices=("50", "80", "gamble", "safe"),
        default=None,
        help="Welcher Forecast-Wert fuer automatische Gebote genutzt wird.",
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Hebt vorhandene eigene Gebote auf den Zielwert an. Standardmaessig werden bestehende Gebote nur gemeldet und nicht veraendert.",
    )
    args = parser.parse_args(parsed_argv)
    if not args.auto_bid and not args.list_only:
        args.auto_bid = True

    if args.update_hour < 0 or args.update_hour > 23:
        parser.error("--update-hour muss zwischen 0 und 23 liegen.")

    try:
        client = forecast_app._build_client(args)
        league = forecast_app._resolve_league(client, league_id=args.league_id, league_name=args.league_name)
        players = forecast_app._market_players_until_next_update(client, league.id, update_hour=args.update_hour)
        if not players:
            next_update = forecast_app._next_market_update_local(update_hour=args.update_hour)
            print(
                "Keine Marktspieler mit Ablauf bis zum naechsten Marktwert-Update gefunden "
                f"({next_update.strftime('%d.%m.%Y %H:%M')})."
            )
            return 0

        environment = forecast_app.prepare_forecast_environment(
            client,
            league.id,
            days=args.days,
        )
    except (KickbaseApiError, KickbaseConfigurationError, ValueError) as error:
        print(f"Fehler: {error}")
        return 1

    next_update = forecast_app._next_market_update_local(update_hour=args.update_hour)
    print(f"Liga: {league.name} ({league.id})")

    if args.auto_bid:
        args.bid_level = _resolve_bid_level(args.bid_level)
        review_items = _run_auto_bids_until_next_update(
            client,
            league=league,
            players=players,
            environment=environment,
            args=args,
        )
        if not parsed_argv:
            print("Direktstart erkannt: Auto-Bid-Modus aktiv. Fuer reine Listenansicht nutze --list-only.")
        if not review_items:
            print(
                "Keine Auto-Gebote gesetzt. Kein Marktspieler bis zum naechsten Marktwert-Update erfuellt aktuell "
                "eine der aktiven Regeln:"
            )
            for rule_description in _auto_bid_rule_descriptions(args):
                print(f"- {rule_description}")
            return 0

        print(
            f"Auto-Gebote bis zum Marktwert-Update am {next_update.strftime('%d.%m.%Y %H:%M')}: {len(review_items)} Spieler"
        )
        print("Aktive Trigger:")
        for rule_description in _auto_bid_rule_descriptions(args):
            print(f"- {rule_description}")
        print(f"Gebotsniveau: {_bid_level_label(args.bid_level)}")
        if args.dry_run:
            print("Dry-Run aktiv: Es wurden keine echten Gebote an Kickbase gesendet.")
        print()
        for index, item in enumerate(review_items, start=1):
            print(_format_auto_bid_review_item(index, item))
            if args.details:
                print(forecast_app.format_summary(item.forecast))
            if index != len(review_items):
                print()
        return 0

    print(
        "Marktliste bis zum naechsten Marktwert-Update "
        f"({next_update.strftime('%d.%m.%Y %H:%M')}): {len(players)} Spieler"
    )
    print()

    for index, player in enumerate(players, start=1):
        forecast = forecast_app.estimate_market_player_bid(
            client,
            league.id,
            player_id=player.player_id,
            days=args.days,
            value_tolerance=args.value_tolerance,
            safe_percentile=args.safe_percentile,
            gamble_percentile=args.gamble_percentile,
            min_samples=args.min_samples,
            forecast_environment=environment,
        )
        print(
            f"{index}. {player.full_name} | Ablauf={forecast_app._format_local_expiry(player.expires_at)} | "
            f"Basis={forecast.projected_market_value_at_expiry} | "
            f"Zocken={forecast.gamble_bid} (+{forecast.gamble_overpay_absolute}) | "
            f"Sicher={forecast.safe_bid} (+{forecast.safe_overpay_absolute}) | "
            f"Trend={forecast_app._describe_trend_label(forecast.target_trend)}"
        )
        if args.details:
            print(forecast_app.format_summary(forecast))
            print()

    return 0


def _run_auto_bids_until_next_update(
    client,
    *,
    league,
    players,
    environment,
    args,
) -> list[AutoBidReviewItem]:
    review_items: list[AutoBidReviewItem] = []
    competition_id = league.competition_id
    if not competition_id:
        raise KickbaseApiError("The selected league does not expose a competition ID.")

    for player in players:
        forecast = forecast_app.estimate_market_player_bid(
            client,
            league.id,
            player_id=player.player_id,
            days=args.days,
            value_tolerance=args.value_tolerance,
            safe_percentile=args.safe_percentile,
            gamble_percentile=args.gamble_percentile,
            min_samples=args.min_samples,
            forecast_environment=environment,
        )
        recent_changes = forecast_app._load_recent_market_value_changes(
            client,
            competition_id=competition_id,
            player_id=player.player_id,
        )
        three_day_delta = _three_day_market_value_delta(recent_changes)
        trigger_reason = _auto_bid_trigger_reason(
            recent_changes,
            market_value=forecast.market_value,
            args=args,
        )
        if trigger_reason is None:
            continue
        target_bid = forecast.safe_bid if args.bid_level == "safe" else forecast.gamble_bid
        own_offer_before_state = client.get_own_offer_state(league.id, player_id=player.player_id)
        own_offer_before = own_offer_before_state.get("offer_price")
        own_offer_after = own_offer_before
        status = "uebersprungen"
        message = None

        try:
            if own_offer_before_state.get("has_own_offer"):
                if args.update_existing and int(own_offer_before or 0) < target_bid:
                    if args.dry_run:
                        status = "dry-run update"
                        own_offer_after = target_bid
                    else:
                        client.cancel_own_offer(league.id, player_id=player.player_id)
                        client.place_offer(league.id, player_id=player.player_id, price=target_bid)
                        own_offer_after_state = client.get_own_offer_state(league.id, player_id=player.player_id)
                        own_offer_after = own_offer_after_state.get("offer_price")
                        status = "aktualisiert"
                else:
                    status = "eigenes Gebot vorhanden"
                    message = (
                        f"Bestehendes Gebot {_format_money_optional(own_offer_before)} wurde nicht veraendert."
                    )
            else:
                if args.dry_run:
                    status = "dry-run neu"
                    own_offer_after = target_bid
                else:
                    client.place_offer(league.id, player_id=player.player_id, price=target_bid)
                    own_offer_after_state = client.get_own_offer_state(league.id, player_id=player.player_id)
                    own_offer_after = own_offer_after_state.get("offer_price")
                    status = "geboten"
        except (KickbaseApiError, ValueError) as error:
            status = "fehler"
            message = str(error)

        review_items.append(
            AutoBidReviewItem(
                player_name=player.full_name,
                player_id=player.player_id,
                recent_changes=recent_changes,
                three_day_delta=three_day_delta,
                trigger_reason=trigger_reason,
                forecast=forecast,
                bid_level=args.bid_level,
                target_bid=target_bid,
                own_offer_before=own_offer_before,
                own_offer_after=own_offer_after,
                status=status,
                message=message,
            )
        )

    return review_items


def _three_day_market_value_delta(changes: tuple[int | None, int | None, int | None]) -> int | None:
    if any(change is None for change in changes):
        return None
    return int(sum(change for change in changes if change is not None))


def _meets_recent_rise_threshold(changes: tuple[int | None, int | None, int | None], minimum_rise: int) -> bool:
    if any(change is None for change in changes):
        return False
    return all(int(change) >= minimum_rise for change in changes if change is not None)


def _meets_one_day_acceleration_threshold(
    changes: tuple[int | None, int | None, int | None],
    minimum_acceleration: int,
) -> bool:
    latest_change, previous_change, _ = changes
    if latest_change is None or previous_change is None:
        return False
    return int(latest_change) > 0 and int(latest_change) >= int(previous_change) + minimum_acceleration


def _meets_trend_reversal_threshold(
    changes: tuple[int | None, int | None, int | None],
    minimum_reversal_rise: int,
) -> bool:
    latest_change, previous_change, _ = changes
    if latest_change is None or previous_change is None:
        return False
    return int(previous_change) < 0 and int(latest_change) >= minimum_reversal_rise


def _meets_three_day_total_rise_threshold(
    changes: tuple[int | None, int | None, int | None],
    minimum_total_rise: int,
    minimum_single_day_change: int,
) -> bool:
    if any(change is None for change in changes):
        return False
    total_rise = _three_day_market_value_delta(changes)
    if total_rise is None or total_rise < minimum_total_rise:
        return False
    return all(int(change) >= minimum_single_day_change for change in changes if change is not None)


def _meets_step_ladder_threshold(
    changes: tuple[int | None, int | None, int | None],
    minimum_three_day_rise: int,
    minimum_two_day_rise: int,
    minimum_one_day_rise: int,
) -> bool:
    latest_change, previous_change, oldest_change = changes
    if latest_change is None or previous_change is None or oldest_change is None:
        return False
    latest = int(latest_change)
    previous = int(previous_change)
    oldest = int(oldest_change)
    return (
        oldest >= minimum_three_day_rise
        and previous >= minimum_two_day_rise
        and latest >= minimum_one_day_rise
        and latest >= previous >= oldest
    )


def _meets_confirmed_recovery_threshold(
    changes: tuple[int | None, int | None, int | None],
    minimum_two_day_rise: int,
    minimum_one_day_rise: int,
    minimum_combined_rise: int,
) -> bool:
    latest_change, previous_change, oldest_change = changes
    if latest_change is None or previous_change is None or oldest_change is None:
        return False
    latest = int(latest_change)
    previous = int(previous_change)
    oldest = int(oldest_change)
    return (
        oldest < 0
        and previous >= minimum_two_day_rise
        and latest >= minimum_one_day_rise
        and latest + previous >= minimum_combined_rise
    )


def _meets_low_price_percentage_threshold(
    changes: tuple[int | None, int | None, int | None],
    *,
    market_value: int | None,
    maximum_market_value: int,
    minimum_one_day_rise_pct: float,
    minimum_combined_rise_pct: float,
) -> bool:
    if market_value is None or market_value <= 0 or market_value > maximum_market_value:
        return False
    if any(change is None for change in changes):
        return False
    total_rise = _three_day_market_value_delta(changes)
    if total_rise is None:
        return False
    reference_market_value = float(market_value)
    latest_rise_pct = int(changes[0]) / reference_market_value * 100
    combined_rise_pct = total_rise / reference_market_value * 100
    return latest_rise_pct >= minimum_one_day_rise_pct and combined_rise_pct >= minimum_combined_rise_pct


def _meets_reacceleration_threshold(
    changes: tuple[int | None, int | None, int | None],
    minimum_three_day_rise: int,
    minimum_two_day_change: int,
    maximum_two_day_change: int,
    minimum_one_day_rise: int,
) -> bool:
    latest_change, previous_change, oldest_change = changes
    if latest_change is None or previous_change is None or oldest_change is None:
        return False
    latest = int(latest_change)
    previous = int(previous_change)
    oldest = int(oldest_change)
    return (
        oldest >= minimum_three_day_rise
        and minimum_two_day_change <= previous <= maximum_two_day_change
        and latest >= minimum_one_day_rise
    )


def _auto_bid_trigger_reason(
    changes: tuple[int | None, int | None, int | None],
    *,
    market_value: int | None,
    args,
) -> str | None:
    reasons: list[str] = []
    if _meets_recent_rise_threshold(changes, int(args.min_three_day_rise)):
        reasons.append(f"1T/2T/3T jeweils >= {forecast_app._format_money(args.min_three_day_rise)}")
    if _meets_one_day_acceleration_threshold(changes, int(args.min_one_day_acceleration)):
        reasons.append(f"1T liegt >= {forecast_app._format_money(args.min_one_day_acceleration)} ueber 2T")
    if _meets_trend_reversal_threshold(changes, int(args.min_trend_reversal_rise)):
        reasons.append(f"Trendwende: 2T negativ und 1T >= {forecast_app._format_money(args.min_trend_reversal_rise)}")
    if _meets_three_day_total_rise_threshold(
        changes,
        minimum_total_rise=int(args.min_three_day_total_rise),
        minimum_single_day_change=int(args.min_three_day_total_single_day_change),
    ):
        reasons.append(
            "Summenregel: "
            f"1T+2T+3T >= {forecast_app._format_money(args.min_three_day_total_rise)} "
            f"und kein Tag < {forecast_app._format_signed_money(args.min_three_day_total_single_day_change)}"
        )
    if _meets_step_ladder_threshold(
        changes,
        minimum_three_day_rise=int(args.min_step_three_day_rise),
        minimum_two_day_rise=int(args.min_step_two_day_rise),
        minimum_one_day_rise=int(args.min_step_one_day_rise),
    ):
        reasons.append(
            "Treppe: "
            f"3T >= {forecast_app._format_money(args.min_step_three_day_rise)}, "
            f"2T >= {forecast_app._format_money(args.min_step_two_day_rise)}, "
            f"1T >= {forecast_app._format_money(args.min_step_one_day_rise)}"
        )
    if _meets_confirmed_recovery_threshold(
        changes,
        minimum_two_day_rise=int(args.min_confirmed_recovery_two_day_rise),
        minimum_one_day_rise=int(args.min_confirmed_recovery_one_day_rise),
        minimum_combined_rise=int(args.min_confirmed_recovery_combined_rise),
    ):
        reasons.append(
            "Erholung bestaetigt: "
            f"3T negativ, 2T >= {forecast_app._format_money(args.min_confirmed_recovery_two_day_rise)}, "
            f"1T >= {forecast_app._format_money(args.min_confirmed_recovery_one_day_rise)}, "
            f"1T+2T >= {forecast_app._format_money(args.min_confirmed_recovery_combined_rise)}"
        )
    if _meets_low_price_percentage_threshold(
        changes,
        market_value=market_value,
        maximum_market_value=int(args.max_low_price_market_value),
        minimum_one_day_rise_pct=float(args.min_low_price_one_day_rise_pct),
        minimum_combined_rise_pct=float(args.min_low_price_combined_rise_pct),
    ):
        reasons.append(
            "Billigspielerregel: "
            f"MW <= {forecast_app._format_money(args.max_low_price_market_value)}, "
            f"1T >= {_format_percentage(args.min_low_price_one_day_rise_pct)} des MW, "
            f"1T+2T+3T >= {_format_percentage(args.min_low_price_combined_rise_pct)} des MW"
        )
    if _meets_reacceleration_threshold(
        changes,
        minimum_three_day_rise=int(args.min_reacceleration_three_day_rise),
        minimum_two_day_change=int(args.min_reacceleration_two_day_change),
        maximum_two_day_change=int(args.max_reacceleration_two_day_change),
        minimum_one_day_rise=int(args.min_reacceleration_one_day_rise),
    ):
        reasons.append(
            "Re-Acceleration: "
            f"3T >= {forecast_app._format_money(args.min_reacceleration_three_day_rise)}, "
            f"2T zwischen {forecast_app._format_signed_money(args.min_reacceleration_two_day_change)} "
            f"und {forecast_app._format_signed_money(args.max_reacceleration_two_day_change)}, "
            f"1T >= {forecast_app._format_money(args.min_reacceleration_one_day_rise)}"
        )
    if not reasons:
        return None
    return " | ".join(reasons)


def _auto_bid_rule_descriptions(args) -> tuple[str, ...]:
    return (
        f"1T/2T/3T jeweils >= {forecast_app._format_money(args.min_three_day_rise)}",
        f"1T >= 2T + {forecast_app._format_money(args.min_one_day_acceleration)}",
        f"2T < 0 und 1T >= {forecast_app._format_money(args.min_trend_reversal_rise)}",
        (
            f"1T+2T+3T >= {forecast_app._format_money(args.min_three_day_total_rise)} "
            f"und kein Tag < {forecast_app._format_signed_money(args.min_three_day_total_single_day_change)}"
        ),
        (
            f"Treppe: 3T >= {forecast_app._format_money(args.min_step_three_day_rise)}, "
            f"2T >= {forecast_app._format_money(args.min_step_two_day_rise)}, "
            f"1T >= {forecast_app._format_money(args.min_step_one_day_rise)} und 1T >= 2T >= 3T"
        ),
        (
            f"Erholung: 3T negativ, 2T >= {forecast_app._format_money(args.min_confirmed_recovery_two_day_rise)}, "
            f"1T >= {forecast_app._format_money(args.min_confirmed_recovery_one_day_rise)}, "
            f"1T+2T >= {forecast_app._format_money(args.min_confirmed_recovery_combined_rise)}"
        ),
        (
            f"Billigspieler bis {forecast_app._format_money(args.max_low_price_market_value)}: "
            f"1T >= {_format_percentage(args.min_low_price_one_day_rise_pct)} des MW und "
            f"1T+2T+3T >= {_format_percentage(args.min_low_price_combined_rise_pct)} des MW"
        ),
        (
            f"Re-Acceleration: 3T >= {forecast_app._format_money(args.min_reacceleration_three_day_rise)}, "
            f"2T zwischen {forecast_app._format_signed_money(args.min_reacceleration_two_day_change)} und "
            f"{forecast_app._format_signed_money(args.max_reacceleration_two_day_change)}, "
            f"1T >= {forecast_app._format_money(args.min_reacceleration_one_day_rise)}"
        ),
    )


def _bid_level_label(bid_level: str) -> str:
    return "80. Perzentil" if bid_level == "safe" else "50. Perzentil"


def _resolve_bid_level(raw_bid_level: str | None) -> str:
    if raw_bid_level is None:
        return _prompt_bid_level()

    normalized = str(raw_bid_level).strip().casefold()
    if normalized in {"80", "safe", "sicher"}:
        return "safe"
    if normalized in {"50", "gamble", "zocken"}:
        return "gamble"
    raise ValueError(f"Unbekanntes Gebotsniveau: {raw_bid_level}")


def _prompt_bid_level() -> str:
    while True:
        raw_value = input("Welches Gebotsniveau willst du fuer Auto-Bid nutzen? (50/80): ").strip().casefold()
        if raw_value in {"80", "safe", "sicher"}:
            return "safe"
        if raw_value in {"50", "gamble", "zocken"}:
            return "gamble"
        print("Bitte 50 oder 80 eingeben.")


def _format_money_optional(value: int | None) -> str:
    if value is None:
        return "kein Gebot"
    return forecast_app._format_money(value)


def _format_percentage(value: float) -> str:
    return f"{float(value):.1f}%"


def _format_auto_bid_review_item(index: int, item: AutoBidReviewItem) -> str:
    lines = [
        f"{index}. {item.player_name} | Status: {item.status}",
        (
            f"   3T-Delta: {forecast_app._format_signed_money(item.three_day_delta)} | "
            f"1T/2T/3T: {forecast_app._format_market_value_change_series(item.recent_changes)}"
        ),
        f"   Trigger: {item.trigger_reason}",
        (
            f"   MW: {forecast_app._format_money(item.forecast.market_value)} | "
            f"Ablauf: {forecast_app._format_local_expiry(item.forecast.target_context.expires_at)} | "
            f"Gebot ({_bid_level_label(item.bid_level)}): {forecast_app._format_money(item.target_bid)}"
        ),
        (
            f"   P50: {forecast_app._format_money(item.forecast.gamble_bid)} | "
            f"P80: {forecast_app._format_money(item.forecast.safe_bid)} | "
            f"Eigenes Gebot vorher: {_format_money_optional(item.own_offer_before)} | "
            f"nachher: {_format_money_optional(item.own_offer_after)}"
        ),
    ]
    if item.message:
        lines.append(f"   Hinweis: {item.message}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())