# Unit Test

Unit tests are in the tests folder

## Configuration

Before running the unit tests, you need to create a secrets folder containing the FOSSOlogy login information at a minimum.

See the [sample file](./sample-scaffold-secrets.json) file for the JSON file structure.

The JSON file has the following fields:
* `default_github_oauth`: A required GitHub OAuth token which is used to access gitHub if no project specific tokens are provided.  See the [GitHub OAuth documentation](https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps) for details on how to create the token.
* `fossology_server`: The URL to the Fossology server (required)
* `fossology_username`: The username Scaffold should use to log into the Fossology server (required)
* `fossology_password`: The password Scaffold should use to log into the Fossology server (required)
* `projects`: Map of a project name to project specific secrets.  The project specific secrets include:
  * `jira`: Optional Jira server and login information
  * `whitesource`: Optional whitesource server authentication information
  * `github_oauth`: Optional project specific GitHub OAuth token
  
You also need to set an environment variables `TRIVY_EXEC_PATH` (set to the Trivy executable) and `NPM_EXEC_PATH` (set to the NPM executable) - otherwise the Trivy tests will fail.

## Running Tests

You can run all the unit tests with the following command from the root of the project:

```
python -m unittest
```

See the [Python Unit Testing documentation](https://docs.python.org/3/library/unittest.html) for more information.