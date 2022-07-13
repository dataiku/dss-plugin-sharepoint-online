# Changelog

## [Version 1.0.12](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.0.12) - Bugfix release - 2022-07-15

- Handles non JSON error pages
- Fixes possible hang on read operations

## [Version 1.0.11](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.0.11) - Feature and bugfix release - 2022-06-21

- Add site path overwrite for site app permissions presets
- List are placed in recycle bin instead of being deleted during overwrite operations
- Better handling of 429 and 503 errors for multiple files uploads

## [Version 1.0.10](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.0.10) - Feature and bugfix release - 2022-02-15

- Add option to overwrite the preset's site and/or folder root from within the custom dataset
- Deleting files now sends them to the recycle bin
- Files checked-in once uploaded
- Session reset on error 403 de-activated by default
- Only one session reset on error 403 now allowed

## [Version 1.0.9](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.0.9) - Feature and bugfix release - 2021-12-17

- Add support for custom domain
- Fix error message during file move
- Fix error message on file delete
- Fix apostrophe in files name

## [Version 1.0.8](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.0.8) - Feature and bugfix release - 2021-07-09

- Improved logging
- Adds form digest value to posts
- Adds retries on get & post following connection reset by peer, throttling events (429 errors)
- Adds session reset following 403 errors
- Fix date format for DSS->SP lists
- Fix issues with trailing slash in site name
- Adds option to select the view
- Fix for short SP date format
