# tap-ms-teams

This is a [Singer](https://singer.io) tap that produces JSON-formatted data
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:

- Pulls raw data from the [Microsoft Graph API](https://docs.microsoft.com/en-us/graph/)
- Extracts the following resources:
  - [users](https://docs.microsoft.com/en-us/graph/api/user-list?view=graph-rest-beta&tabs=http)
  - [groups](https://docs.microsoft.com/en-us/graph/teams-list-all-teams?context=graph%2Fapi%2Fbeta&view=graph-rest-beta)
  - [group_members](https://docs.microsoft.com/en-us/graph/api/group-list-members?view=graph-rest-1.0&tabs=http)
  - [group_owners](https://docs.microsoft.com/en-us/graph/api/group-list-owners?view=graph-rest-1.0&tabs=http)
  - [channels](https://docs.microsoft.com/en-us/graph/api/channel-list?view=graph-rest-1.0&tabs=http)
  - [channel_members](https://docs.microsoft.com/en-us/graph/api/conversationmember-list?view=graph-rest-beta&tabs=http)
  - [channel_tabs](https://docs.microsoft.com/en-us/graph/api/teamstab-list?view=graph-rest-beta)
  - [channel_messages](https://docs.microsoft.com/en-us/graph/api/chatmessage-delta?view=graph-rest-beta&tabs=http)
  - [channel_message_replies](https://docs.microsoft.com/en-us/graph/api/channel-list-messagereplies?view=graph-rest-beta&tabs=http)
  - [conversations](https://docs.microsoft.com/en-us/graph/api/group-list-conversations?view=graph-rest-beta&tabs=http)
  - [conversation_threads](https://docs.microsoft.com/en-us/graph/api/conversation-list-threads?view=graph-rest-beta&tabs=http)
  - [conversation_posts](https://docs.microsoft.com/en-us/graph/api/conversationthread-list-posts?view=graph-rest-beta&tabs=http)
  - [team_drives](https://docs.microsoft.com/en-us/graph/api/drive-get?view=graph-rest-beta&tabs=http#get-the-document-library-associated-with-a-group)

- Outputs the schema for each resource
- Incrementally pulls data based on the input state

## Streams

[users](https://docs.microsoft.com/en-us/graph/api/user-list?view=graph-rest-beta&tabs=http)
  - Data key: value
  - Primary keys: id
  - Replication strategy: Full Table
  - Transformations: camelCase to snake_case
[groups](https://docs.microsoft.com/en-us/graph/teams-list-all-teams?context=graph%2Fapi%2Fbeta&view=graph-rest-beta)
  - Data key: value
  - Primary keys: id
  - Replication strategy: Full Table
  - Transformations: camelCase to snake_case
 [group_members](https://docs.microsoft.com/en-us/graph/api/group-list-members?view=graph-rest-1.0&tabs=http)
  - Data key: value
  - Primary keys: id
  - Replication strategy: Full Table
  - Transformations: camelCase to snake_case
 [group_owners](https://docs.microsoft.com/en-us/graph/api/group-list-owners?view=graph-rest-1.0&tabs=http)
  - Data key: value
  - Primary keys: id
  - Replication strategy: Full Table
  - Transformations: camelCase to snake_case
 [channels](https://docs.microsoft.com/en-us/graph/api/channel-list?view=graph-rest-1.0&tabs=http)
  - Data key: value
  - Primary keys: id
  - Replication strategy: Full Table
  - Transformations: camelCase to snake_case
 [channel_members](https://docs.microsoft.com/en-us/graph/api/conversationmember-list?view=graph-rest-beta&tabs=http)
  - Data key: value
  - Primary keys: id
  - Replication strategy: Full Table
  - Transformations: camelCase to snake_case
 [channel_tabs](https://docs.microsoft.com/en-us/graph/api/teamstab-list?view=graph-rest-beta)
  - Data key: value
  - Primary keys: id
  - Replication strategy: Full Table
  - Transformations: camelCase to snake_case
 [channel_messages](https://docs.microsoft.com/en-us/graph/api/chatmessage-delta?view=graph-rest-beta&tabs=http)
  - Data key: value
  - Primary keys: id
  - Replication strategy: Incremental (query all, filter results)
  - Bookmark: ucreatedDateTime OR lastModifiedDateTime OR deletedDateTime
  - Transformations: camelCase to snake_case
 [channel_message_replies](https://docs.microsoft.com/en-us/graph/api/channel-list-messagereplies?view=graph-rest-beta&tabs=http)
  - Data key: value
  - Primary keys: id
  - Replication strategy: Incremental (query all, filter results)
  - Bookmark: ucreatedDateTime OR lastModifiedDateTime OR deletedDateTime
  - Transformations: camelCase to snake_case
 [conversations](https://docs.microsoft.com/en-us/graph/api/group-list-conversations?view=graph-rest-beta&tabs=http)
  - Data key: value
  - Primary keys: id
  - Replication strategy: Incremental (query all, filter results)
  - Bookmark: lastDeliveredDateTime
  - Transformations: camelCase to snake_case
 [conversation_threads](https://docs.microsoft.com/en-us/graph/api/conversation-list-threads?view=graph-rest-beta&tabs=http)
  - Data key: value
  - Primary keys: id
  - Replication strategy: Incremental (query all, filter results)
  - Bookmark: lastDeliveredDateTime
  - Transformations: camelCase to snake_case
 [conversation_posts](https://docs.microsoft.com/en-us/graph/api/conversationthread-list-posts?view=graph-rest-beta&tabs=http)
  - Data key: value
  - Primary keys: id
  - Replication strategy: Incremental (query all, filter results)
  - Bookmark: lastDeliveredDateTime
  - Transformations: camelCase to snake_case
 [team_drives](https://docs.microsoft.com/en-us/graph/api/drive-get?view=graph-rest-beta&tabs=http#get-the-document-library-associated-with-a-group)
  - Data key: value
  - Primary keys: id
  - Replication strategy: Incremental (query all, filter results)
  - Bookmark: lastModifiedDateTime
  - Transformations: camelCase to snake_case

## Authentication


## Quick Start

1. Install

    Clone this repository, and then install using setup.py. We recommend using a virtualenv:

    ```bash
    > virtualenv -p python3 venv
    > source venv/bin/activate
    > python setup.py install
    OR
    > cd .../tap-ms-teams
    > pip install .
    ```
2. Dependent libraries
    The following dependent libraries were installed.
    ```bash
    > pip install singer-python
    > pip install singer-tools
    > pip install target-stitch
    > pip install target-json
    
    ```
    - [singer-tools](https://github.com/singer-io/singer-tools)
    - [target-stitch](https://github.com/singer-io/target-stitch)
3. Create your tap's `config.json` file which should look like the following:

    ```json
    {
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_API_TOKEN",
        "tenant_id": "YOUR_TENANT_ID",
        "start_date": "2020-05-01T00:00:00Z",
        "user_agent": "tap-ms-teams<api_user_email@your_company.com>"
    }
    ```
    
    Optionally, also create a `state.json` file. `currently_syncing` is an optional attribute used for identifying the last object to be synced in case the job is interrupted mid-stream. The next run would begin where the last job left off.

    ```json
    {
        "bookmarks": {
            "conversation_threads": "2020-08-03T14:21:40.000000Z",
            "team_drives": "2020-07-13T16:55:39.000000Z",
            "channel_messages": "2020-08-12T23:18:03.915000Z",
            "conversation_posts": "2020-08-03T14:21:40.000000Z",
            "conversations": "2020-08-03T14:21:40.000000Z",
            "channel_message_replies": "2020-08-12T23:38:57.582000Z"
        }
    }

    ```

4. Run the Tap in Discovery Mode
    This creates a catalog.json for selecting objects/fields to integrate:
    ```bash
    tap-ms-teams --config config.json --discover > catalog.json
    ```
   See the Singer docs on discovery mode
   [here](https://github.com/singer-io/getting-started/blob/master/docs/DISCOVERY_MODE.md#discovery-mode).

5. Run the Tap in Sync Mode (with catalog) and [write out to state file](https://github.com/singer-io/getting-started/blob/master/docs/RUNNING_AND_DEVELOPING.md#running-a-singer-tap-with-a-singer-target)

    For Sync mode:
    ```bash
    > tap-ms-teams --config tap_config.json --catalog catalog.json > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```
    To load to json files to verify outputs:
    ```bash
    > tap-ms-teams --config tap_config.json --catalog catalog.json | target-json > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```
    To pseudo-load to [Stitch Import API](https://github.com/singer-io/target-stitch) with dry run:
    ```bash
    > tap-ms-teams --config tap_config.json --catalog catalog.json | target-stitch --config target_config.json --dry-run > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```

6. Test the Tap
    
    To [check the tap](https://github.com/singer-io/singer-tools#singer-check-tap) and verify working:
    ```bash
    > tap-ms-teams --config tap_config.json --catalog catalog.json | singer-check-tap > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```
    Check tap resulted in the following:
    ```bash
        The output is valid.
        It contained 114 messages for 13 streams.

            13 schema messages
            75 record messages
            26 state messages

        Details by stream:
        +-------------------------+---------+---------+
        | stream                  | records | schemas |
        +-------------------------+---------+---------+
        | users                   | 10      | 1       |
        | groups                  | 3       | 1       |
        | group_members           | 13      | 1       |
        | group_owners            | 7       | 1       |
        | channels                | 5       | 1       |
        | channel_members         | 5       | 1       |
        | channel_tabs            | 5       | 1       |
        | channel_messages        | 8       | 1       |
        | channel_message_replies | 6       | 1       |
        | conversations           | 3       | 1       |
        | conversation_threads    | 3       | 1       |
        | conversation_posts      | 3       | 1       |
        | team_drives             | 4       | 1       |
        +-------------------------+---------+---------+
    ```
---

Copyright &copy; 2020 Stitch