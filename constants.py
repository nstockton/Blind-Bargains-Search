# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


APPNAME = "Blind Bargains Search"
APPVERSION = "1.0"
AUTHOR = "Nick Stockton"
AUTHOR_EMAIL = "nstockton@gmail.com"
REF = APPNAME.strip().lower().replace(" ", "")
AGENT = "%s %s" % (APPNAME, APPVERSION)
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 480

ABOUT_TEXT = """{program} (V{version})
By {author} <{email}>

Binaries of this product have been made available to you under the Mozilla Public License 2.0 (MPL).
You can obtain a copy of the MPL at http://mozilla.org/MPL/2.0/.
You should have received a copy of the product source code in addition to the product binaries.
If you did not receive a copy of the product source code, please send a request to the distributor of which you obtained these product binaries from.
""".format(program=APPNAME, version=APPVERSION, author=AUTHOR, email=AUTHOR_EMAIL)
