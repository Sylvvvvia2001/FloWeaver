# Home Assistant Integration Notes

The integration must implement `async_setup_entry` and return a boolean.
The coordinator should run first refresh before entity state writes.
Subscriptions should be paired with unsubscribe during unload.
BLE connect should avoid overlap when timeout rate increases.
Cloud requests should back off after HTTP 429 responses.
