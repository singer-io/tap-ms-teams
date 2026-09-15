# Changelog

## 1.1.0
  * Switch authentication from `client_credentials` to `refresh_token` grant to support Stitch platform OAuth flow. [#13](https://github.com/singer-io/tap-ms-teams/pull/13)
  * Write rotated `refresh_token` back to config file when Microsoft issues a new one.
  * Add `refresh_token` to required config keys.

## 1.0.0
  * Bump versions singer-python and requests modules. [#11](https://github.com/singer-io/tap-ms-teams/pull/11)
  * Updated schema files, update composite primary key for groups child streams.[#7](https://github.com/singer-io/tap-ms-teams/pull/7)
  * Fixed unit, integration test cases.[#9](https://github.com/singer-io/tap-ms-teams/pull/9)
  * Add `handle_top_exception` decorator to `main()` for structured error logging. [#12](https://github.com/singer-io/tap-ms-teams/pull/12)

## 0.0.2
  * Added circle
  * Cleaned up pylint complaints

## 0.0.1
  * Initial commit
