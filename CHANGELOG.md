# Changelog

## [Version 1.0.8](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.0.8) - Feature and bugfix release - 2021-07-09

- Improved logging
- Adds form digest value to posts
- Adds retries on get & post following connection reset by peer, throttling events (429 errors)
- Adds session reset following 403 errors
- Fix date format for DSS->SP lists
- Fix issues with trailing slash in site name
- Adds option to select the view
- Fix for short SP date format
