# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from threading import Thread
from urllib2 import Request, urlopen
from urllib import urlencode
try:
	import xml.etree.cElementTree as ET
except ImportError:
	import xml.etree.ElementTree as ET
import socket
import webbrowser

try:
	from bs4 import BeautifulSoup
except ImportError:
	from BeautifulSoup import BeautifulSoup
from ObjectListView import ObjectListView, ColumnDefn
import wx
import wx.lib.dialogs

from constants import *

# Set a timeout in case the server takes too long to respond.
socket.setdefaulttimeout(10)


class OLV(ObjectListView):
	def __init__(self, *args, **kwargs):
		ObjectListView.__init__(self, *args, **kwargs)

	# This method has the undesirable effect of making the program beep when the user presses enter on a list item.
	# Since we don't need it, we will redefine it.
	def _HandleTypingEvent(self, event):
		pass


class MainFrame(wx.Frame):
	def __init__(self, *args, **kwargs):
		wx.Frame.__init__(self, *args, **kwargs)
		# Create the Menu Bar.
		self.menuBar = wx.MenuBar()
		self.SetMenuBar(self.menuBar)
		# This anonymous function lets us bind a handler to a menu item in one line, for convenience.
		menuBind = lambda item, handler: self.Bind(wx.EVT_MENU, handler, item)
		# The File menu.
		self.fileMenu = wx.Menu()
		self.menuBar.Append(self.fileMenu, "&File")
		menuBind(self.fileMenu.Append(wx.ID_ANY, "E&xit"), self.exitEvent)
		# The Help menu.
		self.helpMenu = wx.Menu()
		self.menuBar.Append(self.helpMenu, "&Help")
		menuBind(self.helpMenu.Append(wx.ID_ANY, "Visit &Blind Bargains"), self.launchBlindBargainsEvent)
		menuBind(self.helpMenu.Append(wx.ID_ANY, "&About {0}".format(APPNAME)), self.aboutEvent)
		# Create a panel to help the program look consistent across different platforms.
		panel = wx.Panel(self, wx.ID_ANY)
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(panel, 1, wx.ALL|wx.EXPAND)
		self.SetSizer(sizer)
		# The Search edit box.
		self.searchBoxLabel = wx.StaticText(panel, wx.ID_ANY, "&Search:")
		self.searchBox = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
		# If the user presses enter in the Search Edit Box, perform the search.
		self.searchBox.Bind(wx.EVT_TEXT_ENTER, self.searchEvent)
		# The Submit button.
		self.submitButton = wx.Button(panel, label="Submit")
		self.submitButton.Bind(wx.EVT_BUTTON, self.searchEvent)
		# The Results list view.
		self.resultsListViewLabel = wx.StaticText(panel, wx.ID_ANY, "&Results:")
		self.resultsListView = OLV(panel, wx.ID_ANY, style=wx.LC_REPORT|wx.SUNKEN_BORDER)
		# When the user selects 1 or more list view items:
		self.resultsListView.Bind(wx.EVT_LIST_ITEM_SELECTED, self.itemSelectedEvent)
		# When the user activates a list view item:
		self.resultsListView.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.itemActivatedEvent)
		# Define the columns for the list view.
		columns = [
			ColumnDefn("Name", "left", -1, "name", isEditable=False),
			ColumnDefn("Merchant", "left", -1, "merchant", isEditable=False),
			ColumnDefn("price", "left", -1, "price", isEditable=False)
		]
		self.resultsListView.SetColumns(columns)
		# Set a message to be displayed in the results list view when it contains no items.
		self.resultsListView.SetEmptyListMsg("Empty!")
		# Disable the results list view; We will enable it in the search event if there were results.
		self.resultsListView.Disable()
		# The Description edit box.
		self.descriptionBoxLabel = wx.StaticText(panel, wx.ID_ANY, "&Description:")
		self.descriptionBox = wx.TextCtrl(panel, style = wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_NOHIDESEL)
		# Disable the Description edit box; We will enable it if a selected item has a description.
		self.descriptionBox.Disable()
		# Create a horizontal sizer containing the Search edit box and the Submit button.
		horizontalSizer = wx.BoxSizer()
		horizontalSizer.Add(self.searchBoxLabel)
		horizontalSizer.Add(self.searchBox, proportion = 1, border = 1)
		horizontalSizer.Add(self.submitButton, proportion = 0, border = 1)
		# create a vertical sizer with the controls in the order that they will appear in the panel.  This is *not* the same as the tab order.
		verticalSizer = wx.BoxSizer(wx.VERTICAL)
		verticalSizer.Add(horizontalSizer, proportion = 0, flag = wx.EXPAND, border = 0)
		verticalSizer.Add(self.resultsListViewLabel)
		verticalSizer.Add(self.resultsListView, 1, wx.ALL|wx.EXPAND, 4)
		verticalSizer.Add(self.descriptionBoxLabel)
		verticalSizer.Add(self.descriptionBox, 2, wx.ALL|wx.EXPAND, 4)
		panel.SetSizer(verticalSizer)
		self.Layout()
		self.results = []

	def notify(self, msgType, msgText, msgTitle=""):
		"""Display a notification to the user."""
		# If a title for the dialog wasn't specified, create one from the type that was specified.
		if not msgTitle:
			msgTitle = msgType.capitalize()
		if msgType == "error":
			notifyDialog = wx.MessageDialog(self, message=msgText, caption=msgTitle, style=wx.ICON_ERROR|wx.OK)
		elif msgType == "information":
			notifyDialog = wx.MessageDialog(self, message=msgText, caption=msgTitle, style=wx.ICON_INFORMATION|wx.OK)
		elif msgType == "scrolled":
			notifyDialog = wx.lib.dialogs.ScrolledMessageDialog(self, msgText, msgTitle)
		# If the user presses the OK button, destroy the dialog.
		if notifyDialog.ShowModal() == wx.ID_OK:
			notifyDialog.Destroy()

	def itemSelectedEvent(self, event):
		"""Changes the item description box when a new item is selected."""
		# Disable the Description edit box.  If the item selected has a description, we will enable it.
		self.descriptionBox.Disable()
		itemIndex = event.m_itemIndex
		desc = self.results[itemIndex]["desc"]
		if desc:
			self.descriptionBox.SetValue("{0}\n".format(desc))
			self.descriptionBox.Enable()
		else:
			self.descriptionBox.SetValue("")

	def itemActivatedEvent(self, event):
		"""When a user presses enter on an item, open the merchant page for that item."""
		itemIndex = event.m_itemIndex
		url = self.results[itemIndex]["url"]
		if url:
			webbrowser.open(url)
		else:
			self.notify("information", "There is no merchant URL associated with this result.", "URL not found.")

	def exitEvent(self, event):
		"""Exits the program."""
		self.Destroy()

	def launchBlindBargainsEvent(self, event):
		"""Open the default web browser, and navigate to BlindBargains.com."""
		webbrowser.open("http://www.blindbargains.com")

	def aboutEvent(self, event):
		"""Displays the about dialog."""
		self.notify("scrolled", ABOUT_TEXT, "About {0}".format(APPNAME))

	def searchEvent(self, event):
		"""Runs the search in a new thread."""
		searchThread = Thread(target=self._search)
		searchThread.setDaemon(True)
		searchThread.start()

	def _search(self):
		"""Searches for a product on BlindBargains.com."""
		wx.CallAfter(self.searchBox.SetFocus)
		wx.CallAfter(self.resultsListView.SetObjects, [])
		wx.CallAfter(self.resultsListView.Disable)
		wx.CallAfter(self.descriptionBox.Clear)
		wx.CallAfter(self.descriptionBox.Disable)
		self.results = []
		searchString = self.searchBox.GetValue().strip()
		wx.CallAfter(self.searchBox.Clear)
		if not searchString:
			return self.notify("error", "You need to enter some text in the search box before performing a search.")
		params = {
			"src": REF,
			"format": "xml",
			"kw": searchString
		}
		req = Request(url="http://www.blindbargains.com/search.php")
		req.add_header("User-Agent", AGENT)
		req.add_data(urlencode(params))
		try:
			data = urlopen(req)
		except IOError as e:
			if hasattr(e, "reason"):
				msg = "\tServer is unreachable!\nMake sure you are connected to the internet."
			elif hasattr(e, "code"):
				msg = "The server couldn't fulfill the request. (Error {0})".format(e.code)
			else:
				msg = "Unknown IO Error."
			return self.notify("error", msg)
		try:
			xml = ET.parse(data)
		except ET.ParseError:
			return self.notify("error", "Invalid XML feed.")
		data.close()
		resultCount = xml.findtext("resultCount")
		if resultCount == "0":
			return self.notify("information", "No results found.\nPlease Try again.", "Nothing Found.")
		for item in xml.findall("items/item"):
			desc = item.findtext("desc")
			desc = "\n".join(BeautifulSoup(desc).findAll(text=True)).strip()
			result = {
				"name": item.findtext("name"),
				"url": item.findtext("url"),
				"merchant": item.findtext("merchant"),
				"price": item.findtext("price"),
				"desc": desc
			}
			self.results.append(result)
		wx.CallAfter(self.resultsListView.SetObjects, self.results)
		wx.CallAfter(self.resultsListView._SelectAndFocus, 0)
		wx.CallAfter(self.resultsListView.Enable)
		wx.CallAfter(self.resultsListView.SetFocus)


app = wx.App(redirect=False)
window = MainFrame(None, title=APPNAME, size=(WINDOW_WIDTH, WINDOW_HEIGHT))
app.SetTopWindow(window)
window.Center()
window.ShowFullScreen(True,wx.FULLSCREEN_NOTOOLBAR)
app.MainLoop()
