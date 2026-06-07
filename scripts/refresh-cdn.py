#!/usr/bin/env python3
import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import sys
import uuid
from urllib.parse import quote
from urllib.request import Request, urlopen


def percent_encode(value: str) -> str:
    return quote(value, safe="~")


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(2)
    return value


def main() -> None:
    access_key_id = require_env("ALIYUN_ACCESS_KEY_ID")
    access_key_secret = require_env("ALIYUN_ACCESS_KEY_SECRET")
    cdn_domain = require_env("CDN_DOMAIN")
    cdn_scheme = os.environ.get("CDN_SCHEME", "http")
    object_path = os.environ.get("CDN_REFRESH_OBJECT_PATH", f"{cdn_scheme}://{cdn_domain}/")

    params = {
        "Format": "JSON",
        "Version": "2018-05-10",
        "AccessKeyId": access_key_id,
        "SignatureMethod": "HMAC-SHA1",
        "Timestamp": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "SignatureVersion": "1.0",
        "SignatureNonce": str(uuid.uuid4()),
        "Action": "RefreshObjectCaches",
        "ObjectType": "Directory",
        "ObjectPath": object_path,
    }

    canonicalized_query = "&".join(
        f"{percent_encode(key)}={percent_encode(params[key])}" for key in sorted(params)
    )
    string_to_sign = f"GET&%2F&{percent_encode(canonicalized_query)}"
    signature = base64.b64encode(
        hmac.new(
            f"{access_key_secret}&".encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("utf-8")

    url = f"https://cdn.aliyuncs.com/?Signature={percent_encode(signature)}&{canonicalized_query}"
    request = Request(url, headers={"User-Agent": "beex-admin-deploy/1.0"})

    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    print(
        json.dumps(
            {
                "requestId": payload.get("RequestId"),
                "refreshTaskId": payload.get("RefreshTaskId"),
                "objectPath": object_path,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
