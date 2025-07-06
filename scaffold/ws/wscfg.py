# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

def _getWSSecretsApikey(cfg, prj):
    ws_secrets = cfg._secrets._ws.get(prj._name, None)
    if ws_secrets is None:
        print(f"{prj._name}: unable to get apikey; no WS secrets found")
        return ""
    return ws_secrets._ws_api_key

def _getWSSecretsUserkey(cfg, prj):
    ws_secrets = cfg._secrets._ws.get(prj._name, None)
    if ws_secrets is None:
        print(f"{prj._name}: unable to get userkey; no WS secrets found")
        return ""
    return ws_secrets._ws_user_key

def _getWSSecretsApikeyOverride(cfg, prj, sp):
    ws_secrets = cfg._secrets._ws.get(prj._name, None)
    if ws_secrets is None:
        print(f"{prj._name}: unable to get apikey override; no WS secrets found")
        return ""
    return ws_secrets._ws_api_key_overrides.get(sp._name, "")

# get the user key
# FIXME can a subproject override this?
def getWSUserKey(cfg, prj):
    return _getWSSecretsUserkey(cfg, prj)

# get the actual expected WS org token (API key) for this
# subproject from secrets, taking prj and sp overrides into account
def getWSOrgToken(cfg, prj, sp):
    any_override = _getWSSecretsApikeyOverride(cfg, prj, sp)
    if any_override != "":
        return any_override
    return _getWSSecretsApikey(cfg, prj)

# get the actual expected WS product name for this subproject,
# taking prj and sp overrides into account
def getWSProductName(cfg, prj, sp):
    if sp._ws_override_product != "":
        return sp._ws_override_product

    return sp._name

# get the actual expected WS project name for this subproject,
# taking prj and sp overrides into account
def getWSProjectName(cfg, prj, sp):
    if sp._ws_override_project != "":
        return sp._ws_override_project

    return sp._name

# get the actual environment variables to be used,
# taking prj and sp overrides into account
def getWSEnv(cfg, prj, sp):
    env = {}
    for k, v in cfg._ws_default_env.items():
        env[k] = v
    for k, v in prj._ws_env.items():
        env[k] = v
    for k, v in sp._ws_env.items():
        env[k] = v
    return env

# is WS enabled for this project / subproject, taking overrides
# into account?
def isWSEnabled(cfg, prj, sp):
    if not prj._ws_enabled:
        return False
    if sp._ws_override_disable_anyway:
        return False
    return True
