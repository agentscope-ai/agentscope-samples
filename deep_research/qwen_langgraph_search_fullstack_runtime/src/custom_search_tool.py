# -*- coding: utf-8 -*-
import os
import uuid
import random
import string
import time
from base64 import b64encode
from hashlib import sha256
from hmac import new as hmac_new
from typing import List, Dict, Any

import requests
from .utils import format_time


class CustomSearchTool:
    def __init__(self, search_engine: str = "quark"):
        assert search_engine in ["quark"]
        self.search_engine = search_engine

        if self.search_engine == "quark":
            self.search_func = self._quark_search
        else:
            raise NotImplementedError

        self.search_engine = search_engine

    def search(
        self,
        query: str,
    ) -> List[Dict[str, Any]]:
        """
        Execute search and return the results
        :param query:
        :param num_results:
        :return:
        """

        return self.search_func(query)

    def search_quark_to_b_signature(self, user_name, timestamp, salt: str, sk):
        """
        signature
        :param user_name: username
        :param timestamp: timestamp
        :param salt: salt
        :param sk:
        :return:
        """
        data = f"{user_name}{timestamp}{salt}{sk}"
        hashed = hmac_new(sk.encode("utf-8"), data.encode("utf-8"), sha256)
        return b64encode(hashed.digest()).decode("utf-8")

    def search_quark_to_b_gen_token(self, user_name: str, sk: str):
        """
        get token
        :param user_name:
        :param sk:
        :return:
        """
        timestamp = str(int(time.time() * 1000))
        salt = "".join(random.choice(string.ascii_lowercase) for _ in range(6))
        sign = self.search_quark_to_b_signature(user_name, timestamp, salt, sk)
        postBody = {
            "userName": user_name,
            "timestamp": timestamp,
            "salt": salt,
            "sign": sign,
        }
        url = "https://zx-dsc.sm.cn/api/auth/token"
        headers = {"content-type": "application/json"}
        response = requests.post(url, json=postBody, headers=headers)
        data = response.json()
        token = data["result"]["token"]
        return token

    def _quark_search(self, query: str):
        ak = os.getenv("QUARK_AK", "")
        sk = os.getenv("QUARK_SK", "")
        token = self.search_quark_to_b_gen_token(ak, sk)
        url = "https://zx-dsc.sm.cn/api/resource/s_agg/ex/query"
        querystring = {
            "page": "1",
            "q": query,
        }
        request_id = str(uuid.uuid4())
        headers = {
            "Authorization": f"Bearer {token}",
            "request-id": request_id,
        }
        try:
            response = requests.get(url, headers=headers, params=querystring)
            if response.status_code == 200:
                data = response.json()
                if (
                    data.get("items", {}).get("@attributes", {}).get("status")
                    == "OK"
                    and data.get(
                        "items",
                    )
                    and data.get("items", {}).get("item")
                ):
                    items = data.get("items").get("item")
                    formated_items = []
                    for item in items:
                        formated_items.append(
                            {
                                "title": item["title"],
                                "url": item["url"],
                                "snippet": item["desc"],
                                "content": item["MainBody"],
                                "publish_date": format_time(item.get("time")),
                                "site_name": item.get("site_name", ""),
                            },
                        )
                    return formated_items
                else:
                    return []
            else:
                return []
        except Exception as e:
            print(f"Quark search failed: {e}")
            return []
