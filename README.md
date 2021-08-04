# Run Salt States via Git Webhook

Process incoming git webhooks and run a specified Salt state.

Environment variable configuration:
* `GITHOOK_SECRET` - Secret for validation of GitHub or GitLab payloads.
* `LOG_LEVEL`      - (optional) Log level for app messages. Defaults to INFO.
* `SALT_STATE`     - State name to run using the Caller client (salt-call).

A `git_ref` key is passed in Pillar to the state in "refs/(heads|tags)/(name)" format.

Example State:
```
    {%- set ref = pillar.get("git_ref", "").split("/") | last %}
    
    sync_git_{{ref}}_env:
      git.latest:
        - name: https://github.com/eitrtechnologies/idem-azurerm.git
        - target: /srv/salt/{{ ref }}
        - rev: {{ ref }}
        - branch: {{ ref }}
```
