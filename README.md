# Polkka Aromi Menu for Home Assistant

Shows the daily menu from a [Polkka Aromi Menu](https://aromimenu.cgisaas.fi/) site
(used by many Finnish daycares/schools/restaurants) as a Home Assistant calendar,
with one all-day event per day listing that day's meals and dishes.

Also adds three sensors — `sensor.*_breakfast`, `sensor.*_lunch`, `sensor.*_snack` —
each holding today's dishes for that meal (matched by keyword against the API's meal
name, so it still works if the site adds other meals like "Afternoon snack").

## Install

Copy `custom_components/polkka_menu` into your Home Assistant `config/custom_components/`
directory (or add this repo to HACS as a custom repository), then restart Home Assistant.

## Set up

You need the request URL, restaurant ID, and request body your daycare's menu page
sends. To find them:

1. Open your daycare's Polkka menu page in a desktop browser.
2. Open dev tools (F12) → **Network** tab, reload the page.
3. Find the POST request to a URL ending in `/RestaurantMeals`.
4. In Home Assistant, go to **Settings → Devices & services → Add integration →
   Polkka Aromi Menu** and fill in:
   - **Request URL**: the request URL *without* the `?Id=...` query string, e.g.
     `https://aromimenu.cgisaas.fi/PolkkaAromieMenus/EN/Default/<region>/<site>/api/Common/Restaurant/RestaurantMeals`
   - **Restaurant ID**: the value of the `Id` query parameter on that request.
   - **Request body**: the full JSON body of that POST request, copied as-is.
5. If the site exposes diet restrictions (lactose-free, vegan, allergies, etc.) for
   that request body's `DietGroupId`, you'll be asked to pick which ones to filter
   the menu for. Leave all unchecked to get the full, unrestricted menu.

Diet restrictions can be changed later from the integration's **Configure** button
without redoing the whole setup.

## Notes

- The integration polls every 6 hours, and always fetches live when the calendar UI
  is browsed to a date range outside the cached window.
- Only fields present in the pasted request body are sent to the API; this
  integration doesn't hardcode any daycare/restaurant/diet-group specific IDs.
