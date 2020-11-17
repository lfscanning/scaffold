# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import json
import os
import sys
import time

import requests

# make and verify successful WS API call
# return dict of full response or empty dict if couldn't
# be validated
def _ws_post(js_dict):
    # make API call
    r = requests.post("https://saas.whitesourcesoftware.com/api/v1.3", json=js_dict)
    if r.status_code != requests.codes.ok:
        print(f"WS API call failed for org_token {js_dict.org_token}: got status code {r.status_code}")
        return {}

    # parse content and verify success response
    try:
        rj = json.loads(r.content.decode('utf-8'))
    except json.JSONDecodeError as e:
        print(f"WS API call responded with 200 but returned invalid JSON content: {e.msg}")
        return {}

    message = rj.get("message", "")
    if message[0:7] != "Success":
        print(f"WS API call responded with 200 but did not return success message: {message}")
        return {}

    return rj

# returns hash of product name to product token, for all
# products in the org
def getAllProductsAndTokens(userkey, org_token):
    # make API call
    js_dict = {
        "requestType": "getAllProducts",
        "orgToken": org_token,
        "userKey": userkey,
    }
    print(f"WSAPI: making getAllProducts call")
    rj = _ws_post(js_dict)
    if rj == {}:
        return None

    # parse response
    products = {}
    for product_dict in rj.get("products", []):
        name = product_dict.get("productName", "")
        token = product_dict.get("productToken", "")
        products[name] = token
    return products

# returns hash of project name to project token, for all
# projects in all products in the specified __org__, given the
# product tokens that were already retrieved
# note that each product is expected to have only one project,
# with this current model
def getAllProjectsAndTokens(userkey, product_tokens):
    projects = {}
    num_product_tokens = len(product_tokens)
    current_token = 0

    for product_name, product_token in product_tokens.items():
        # make API call
        js_dict = {
            "requestType": "getAllProjects",
            "productToken": product_token,
            "userKey": userkey,
        }
        current_token += 1
        print(f"WSAPI: making getAllProjects call ({current_token}/{num_product_tokens})")
        rj = _ws_post(js_dict)
        if rj == {}:
            return None

        # parse response
        for project_dict in rj.get("projects", []):
            name = project_dict.get("projectName", "")
            token = project_dict.get("projectToken", "")
            projects[name] = token

        # sleep a bit, because we're making a bunch of API calls
        # potentially
        time.sleep(1)

    return projects

# returns token for product with given name
# will call API to get list of all tokens if not already cached
def getProductToken(cfg, prj, ws_product_name, userkey, org_token):
    # check and cache tokens if not present
    if prj._ws_product_tokens == {} or prj._ws_project_tokens == {}:
        prj._ws_product_tokens = getAllProductsAndTokens(userkey, org_token)
        prj._ws_project_tokens = getAllProjectsAndTokens(userkey, prj._ws_product_tokens)

    # check to make sure we actually got some
    if prj._ws_product_tokens == None or prj._ws_project_tokens == None:
        print(f"Error retrieving product or project tokens from WSAPI; bailing")
        return ""

    return prj._ws_product_tokens.get(ws_product_name, "")

# returns token for project with given name
# will call API to get list of all tokens if not already cached
def getProjectToken(cfg, prj, ws_project_name, userkey, org_token):
    # check and cache tokens if not present
    if prj._ws_product_tokens == {} or prj._ws_project_tokens == {}:
        prj._ws_product_tokens = getAllProductsAndTokens(userkey, org_token)
        prj._ws_project_tokens = getAllProjectsAndTokens(userkey, prj._ws_product_tokens)

    # check to make sure we actually got some
    if prj._ws_product_tokens == None or prj._ws_project_tokens == None:
        print(f"Error retrieving product or project tokens from WSAPI; bailing")
        return ""

    return prj._ws_project_tokens.get(ws_project_name, "")

# create product with the given name in the specified org
# returns new product's token after caching it, or "" on failure
# DOES NOT CHECK FIRST to see whether product is present
def createProduct(cfg, prj, userkey, org_token, product_name):
    # make API call
    js_dict = {
        "requestType": "createProduct",
        "orgToken": org_token,
        "userKey": userkey,
        "productName": product_name,
    }
    print(f"WSAPI: making createProduct call for {product_name}")
    rj = _ws_post(js_dict)
    if rj == {}:
        print(f"Failed to create product {product_name}")
        return ""

    # parse response
    product_token = rj.get("productToken", "")
    if product_token == "":
        print(f"Tried to create product {product_name} but did not get product token in response")
        return ""

    prj._ws_product_tokens[product_name] = product_token
    return product_token

# create project with the given name in the specified product
# returns new project's token after caching it, or "" on failure
# DOES NOT CHECK FIRST to see whether project is present
def createProject(cfg, prj, userkey, product_token, project_name):
    # make API call
    js_dict = {
        "requestType": "createProject",
        "productToken": product_token,
        "userKey": userkey,
        "projectName": project_name,
    }
    print(f"WSAPI: making createProject call for {project_name}")
    rj = _ws_post(js_dict)
    if rj == {}:
        print(f"Failed to create project {project_name}")
        return ""

    # parse response
    project_token = rj.get("projectToken", "")
    if project_token == "":
        print(f"Tried to create project {project_name} but did not get project token in response")
        return ""

    prj._ws_project_tokens[project_name] = project_token
    return project_token
