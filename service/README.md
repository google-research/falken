# Falken Service

You can run the Falken service on your machine by following the steps below.

## Install dependencies

Install the following dependencies:

- [Python 3.7 or above](https://www.python.org/downloads/)
- [pip](https://pip.pypa.io/en/stable/installing/)
- [openssl](https://wiki.openssl.org/index.php/Binaries)

## Set up directories (Optional)

Falken runs on your local file system.

You can optionally specify `--root_dir` and `--ssl_dir` to the `launcher.py`
script to configure where Falken stores data and generates / loads certs
respectively. If these flags are empty Falken data and certs are stored in
the `service` directory.

The directory specified by `--root_dir` will be populated with Falken resources
such as projects, brains, sessions, etc.
The directory specified by `--ssl_dir` will be used to store your SSL
certificates for connecting your client to the service.

By default, Falken uses the test `cert.pem` and `key.pem` files in the service
directory, but it will automatically call openssl to generate a new key pair if
you specify `--ssl_dir`.

## Launch the Service

Run the following command at the root of the falken repo:
```
python service/launcher.py --project_ids falken_test --generate_sdk_config
```

Or if you set up your own directories:
```
python service/launcher.py --root_dir /path/to/falken_root_dir/ --ssl_dir
/path/to/falken_ssl_dir/ --project_ids falken_test --generate_sdk_config
```

The `--project_ids` flag generates a project and API key to connect to Falken.
If you want to create multiple projects, you can specify them by repeating the
argument:

```
--project_ids falken_test --project_ids falken_test_2
```

`--generate_sdk_config` autogenerates a falken_config.json that can be used by
your client to connect to the service at `service/tools/falken_config.json`.

When using `--generate_sdk_config`, do not use multiple project IDs, since a
JSON config is per-project.

After running this command, you should see some output, such as the API key
that was generated for the project ID you requested, and
```
Waiting for assignment.
```
logged in a loop.

## Test the Service

Now that you have your service running, you can integrate the SDK with your
game.
To do this, follow instructions to integrate the C++ SDK [here](
../sdk/cpp/README.md) or the Unity SDK [here](../sdk/unity/README.md).
