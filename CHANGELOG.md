# Changelog

## [Version 1.1.6](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.1.6) - Bugfix release - 2025-04-01

- Fix issue with 255+ chars file paths. The new limit is 400 chars, imposed by SharePoint's API.

## [Version 1.1.5](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.1.5) - Bugfix release - 2024-12-04

- Reduce log verbosity around retry functions
- Retry every connection in case of a HTTP error 500

## [Version 1.1.4](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.1.4) - Feature release - 2024-07-16

- Fix writing when using presets with no root folder defined
- Limit string length to the 255 characters SharePoint limit
- Fix read and write issues with file names / paths containing # or %

## [Version 1.1.3](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.1.3) - Feature release - 2024-06-04

- Add login with Azure AD app certificate

## [Version 1.1.2](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.1.2) - Bugfix release - 2024-05-28

- Fix path creation inside read-only parent directory

## [Version 1.1.1](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.1.1) - Bugfix release - 2024-01-24

- Fix file creation when using username / password authentication
- Updated code-env descriptor for DSS 12

## [Version 1.1.0](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.1.0) - Feature release - 2023-11-10

- Adding an **Append to list** recipe
- Updated code-env descriptor for DSS 12

## [Version 1.0.16](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.0.16) - Bugfix release - 2024-01-24

- Fix file creation when using username / password authentication

## [Version 1.0.15](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.0.15) - Feature release - 2023-11-10

- Adding an **Append to list** recipe

## [Version 1.0.14](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.0.14) - Bugfix release - 2023-04-18

- Updated code-env descriptor for DSS 12

## [Version 1.0.13](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.0.13) - Bugfix release - 2022-10-13

- Allow file to be overwritten using export recipe without `clear before export` activated
- Fix folder creation when root path is left empty

## [Version 1.0.12](https://github.com/dataiku/dss-plugin-sharepoint-online/releases/tag/v1.0.12) - Feature and bugfix release - 2022-07-19

- Add site path overwrite for username / password permissions presets
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
