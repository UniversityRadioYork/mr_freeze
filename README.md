# I am Mr. Freeze!

I'm a set of tools to make it easier to work with Icecast in production.

Specifically, I can do

* Source authentication

I can't yet do, but would like to do:

* Auth against a database (currently just a local file
* Listener statistics

## Installation

Clone this repository. Run `python3 -m venv venv`, and `venv/bin/pip install -r requirements.txt`.

Copy `mr_freeze.cfg.example` to `mr_freeze.cfg` and modify it according to your needs.

## Usage

To run it, `venv/bin/python server.py`.

### Source Authentication

The format of the users file is as follows:

```
<username>:<bcrypt-hash> attr=value attr2=value2
```
