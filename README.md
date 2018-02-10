birdnest-posts
==============

Micro blogging platform. https://posts.taybird.com/

Credentials
-----------

An s3 bucket must be provided with the following objects populated with valid credentials:

* **account.key:** a unique id to create a LetsEncrypt identity
* **yubico:** Yubico API Tokens in format `userid,secretkey`
* **yubikey_key_id:** 12-digit identifier of owner's yubikey
