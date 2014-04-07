# ILL Request System v.1.0.0
# Original Version Author: Joshua Benton Wright / February 15, 2013
# This and all associated code/script files licensed under the GNU General Public License, Version 3.
# To Do:
#	- needs comprehensive server-side input validation ASAP
#	- should users be able to register themselves as art eds?  Maybe submit a request for that status?
#	- add more searchable fields
#	- css needs cleaning up
#	- some 

import cgi
import datetime
import urllib
import webapp2
import random
import string
import logging
import HTMLParser

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import search
from google.appengine.api import mail

import jinja2
import os

_INDEX_NAME="illrequest_index" #used for storage/refrencing a search terms document associated with an ill request.
_ADMIN_ACCOUNT="illrequest@gmail.com"

jinja_environment = jinja2.Environment(
loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),extensions=['jinja2.ext.with_'])

class ILLRequest(db.Model):
	#Models an an interlibrary loan request for a source.
	title = db.StringProperty(multiline=True) #the title of the source itself
	author = db.StringProperty(multiline=True) #the author
	workEditor = db.StringProperty(multiline=True) 
	publicationDate = db.DateTimeProperty(auto_now_add=True)
	volumeNumber = db.StringProperty(multiline=True)
	seriesName = db.StringProperty(multiline=True)
	pinCite = db.StringProperty(multiline=True)
	resourceType = db.StringProperty(multiline=True) #a book, a newspaper, etc.
	description = db.StringProperty(multiline=True)
	requester = db.StringProperty(multiline=True) #email of the user who requested this.
	requesterFullName = db.StringProperty(multiline=True)
	#technically, the following four properties could be pulled on demand from an article editor object referenced by key, but I've elected to duplicate the data here instead; it's kind of an edge case, but if an ILL request outlived the art ed's participation on the journal, we wouldn't want an ill request to lose this data if the administrator deleted the associated article editor object without considering the rammifications.
	articleEditor = db.StringProperty(multiline=True)
	articleEditorEmail = db.StringProperty(multiline=True)
	execEditor = db.StringProperty(multiline=True)
	execEditorEmail = db.StringProperty(multiline=True)
	articleAuthor = db.StringProperty(multiline=True)
	articleTitle = db.StringProperty(multiline=True)
	journalVolume = db.StringProperty(multiline=True)
	fullCitation = db.StringProperty(multiline=True)
	status = db.StringProperty(multiline=True) #unsent, pending, received
	specialStatus = db.StringProperty(multiline=True) 
	specialNotes = db.StringProperty(multiline=True)
	requestedDate = db.DateTimeProperty(auto_now_add=True)
	dueDate = db.DateTimeProperty()
	canRenew = db.StringProperty(multiline=True)
	hasRenewed = db.BooleanProperty()
	library	= db.StringProperty(multiline=True)
	modifiedBy = db.ListProperty(str,verbose_name=None,default=None)
	modifiedOn = db.ListProperty(datetime.date,verbose_name=None,default=None)
	modifiedWhy = db.ListProperty(str,verbose_name=None,default=None)
	
	def regenerate_search_document(self):
		#should be called if any searchable attribute of the ILLRequest changes.  N.B. this can only be called after an ILLRequest has been *.put() into the database and a valid key exists. 
		search.Index(name=_INDEX_NAME).delete(str(self.key()))
		#for simplicity, the search document gets the same key as its associated ILLRequest database entry.
		ill_document = create_document(str(self.key()), self.title, self.author, self.publicationDate, self.description, self.articleAuthor,self.articleEditor, self.status)
		search.Index(name=_INDEX_NAME).put(ill_document)

def create_document(dbKey, title, author, publicationDate, description, articleAuthor, articleEditor, status):
	#Creates a searchable terms document for an illrequest database entry.  Note that if the app engine dashboard is used to delete an ILLRequest, the associated document will be orphaned.  This can lead to spurious search results.  There are a couple of ways to deal with this problem:
	# 	* for serious cases, the admin page has an option to find and trash all orphans and force extant ill requests to regenerate their search documents.  This is the nuclear option - it's resource intensive.
	#	* displayed ill search listings each include a button that allows the administrator to force the associated ill request to regenerate its search terms.  If this routine is invoked and the referenced ill request no longer exists, the search terms document that produced the search listing will simply be trashed. 
	#A similar, though less serious, problem arises if an ill request object is edited through the dashboard - the associated search document will be stale.  Again, the prior remedies apply.
	return search.Document(dbKey,
		fields=[search.TextField(name='title', value=title),
				search.TextField(name='author', value=author),
				search.TextField(name='description', value=description),
				search.TextField(name='articleAuthor', value=articleAuthor),
				search.TextField(name='articleEditor', value=articleEditor),
				search.DateField(name='publicationDate', value=publicationDate),
				search.TextField(name='status', value=status)],
				language='en')
					
class FunnyQuote(db.Model):
	#Models an amusing or thought-provoking quote
	quote = db.StringProperty(multiline=True)
	author = db.StringProperty(multiline=True)
	submitter = db.StringProperty(multiline=True)
	submittedDate = db.DateTimeProperty(auto_now_add=True)
  
def get_quote():
	funny_quotes = FunnyQuote.all()
	funny_quote_count = funny_quotes.count()
	quote_count = None
	funny_quote = None
	if funny_quote_count > 0:	
		quote_count = random.randint(0, funny_quote_count-1)
		inc = 0
		for quote in funny_quotes:
			if inc == quote_count:
				funny_quote = quote
				break
			inc = inc + 1
		return funny_quote	

class ArticleAuthor(db.Model):
	name = db.StringProperty(multiline=True)
	title = db.StringProperty(multiline=True)
	volume = db.StringProperty(multiline=True)

class ArticleEditor(db.Model):
	name = db.StringProperty(multiline=True)
	title = db.StringProperty(multiline=True)
	author = db.StringProperty(multiline=True)
	volume = db.StringProperty(multiline=True)
	email = db.StringProperty(multiline=True)
	execEditor = db.StringProperty(multiline=True)
	execEmail = db.StringProperty(multiline=True)
	
# class ArticleSeniorEditor(db.Model):
# 	name = db.StringProperty()
# 	email = db.StringProperty()

class Library(db.Model):
	name = db.StringProperty(multiline=True)

def illrequest_key(illrequestGroup_name=None):
  	"""Constructs a Datastore key for a ill request entity with illrequestGroup_name."""
	return db.Key.from_path('ILLRequest', illrequestGroup_name or 'default_illrequestGroup')

def quote_key(quoteGroup_name=None):
  	"""Constructs a Datastore key for a funny quote entity with quoteGroup_name."""
	return db.Key.from_path('FunnyQuote', quoteGroup_name or 'default_quoteGroup')
	
def articleAuthor_key(articleAuthorGroup_name=None):
  	"""Constructs a Datastore key for an author entity with articleAuthorGroup_name."""
	return db.Key.from_path('ArticleAuthor', articleAuthorGroup_name or 'default_articleAuthorGroup')

def articleEditor_key(articleEditorGroup_name=None):
  	"""Constructs a Datastore key for an editor entity with articleEditorGroup_name."""
	return db.Key.from_path('ArticleEditor', articleEditorGroup_name or 'default_articleEditorGroup')

def library_key(libraryGroup_name=None):
  	"""Constructs a Datastore key for a library entity with libraryGroup_name."""
	return db.Key.from_path('Library', libraryGroup_name or 'default_libraryGroup')

class MainPage(webapp2.RequestHandler):
	def get(self):

		#				illrequest_name=self.request.get('illrequest_name')
		#				illrequest_query = ILLRequest.all().ancestor(
		#				illrequest_key(illrequest_name)).order('-title')
		#					 illrequests = illrequest_query.fetch(100)
		
		#initialize various ill request queries and count variables, etc.
		#re: the *.all()'s, note that a query isn't executed until its results are accessed
		
# 		doc_index = search.Index(name=_INDEX_NAME)
# 
# 		while True:
# 			# Get a list of documents populating only the doc_id field and extract the ids.
# 			document_ids = [document.doc_id
# 			                for document in doc_index.get_range(ids_only=True)]
# 			if not document_ids:
# 			    break
# 			# Delete the documents for the given ids from the Index.
# 			doc_index.delete(document_ids)
			
		funny_quote = get_quote()	
		illrequestGroup_name = self.request.get('illrequestGroup_name')
		pending = ILLRequest.all().ancestor(illrequest_key(illrequestGroup_name))
		pending_count = 0
		unsent = ILLRequest.all().ancestor(illrequest_key(illrequestGroup_name))
		unsent_count = 0
		received = ILLRequest.all().ancestor(illrequest_key(illrequestGroup_name))
		received_count = 0
		registered_user_email = None
		nickname = None
		today = datetime.date.today()
		
		is_admin_user = users.is_current_user_admin()
		
		if users.get_current_user():
				 #if the user is logged in, let's gather some overview information for his/her welcome page and button bar
			if not is_admin_user:
				pending.filter("requester = ",users.get_current_user().email())
				unsent.filter("requester = ",users.get_current_user().email())
				received.filter("requester = ",users.get_current_user().email())
			
			pending.filter("status =","pending")
			unsent.filter("status =","unsent")
			received.filter("status =","received")
			
			pending_count = pending.count()
			unsent_count = unsent.count()
			received_count = received.count()
			
			registered_user_email = users.get_current_user().email()		 
			loginout_url = users.create_logout_url(self.request.uri)
			nickname = users.get_current_user().nickname()
			loginout_linktext = 'Logout'
		else:
			#pending.filter("requester = ","quite_absolutely_no_one_at_all")
			#otherwise, just get the login button ready
			loginout_url = users.create_login_url(self.request.uri)
			loginout_linktext = 'login'
		
		#we have to map app variables to template values so they can be accessible from the associated html script	
		template_values = {
			'funny_quote': funny_quote,
			'pending': pending,
			'unsent': unsent,
			'received': received,
			'pending_count': pending_count,
			'unsent_count': unsent_count,
			'received_count': received_count,
			'registered_user_email': registered_user_email,
			'loginout_url': loginout_url,
			'loginout_linktext': loginout_linktext,
			'nickname': nickname,
			'today': today,
			'is_admin_user': is_admin_user,
			}
		#with the data above, we now render the template and push it to the client
		template = jinja_environment.get_template('index.html')
		self.response.out.write(template.render(template_values))

class AdminPage(webapp2.RequestHandler):
	def get(self):
		funny_quote = get_quote()
   		loginout_url = None
		loginout_linktext = "logout"
   		registered_user_email = None
   		is_admin_user = users.is_current_user_admin()
   		
   		articleEditorGroup_name = self.request.get('articleEditorGroup_name')
   		article_editors = ArticleEditor.all().ancestor(articleEditor_key(articleEditorGroup_name))
   		
   		libraryGroup_name = self.request.get('libraryGroup_name')
   		libraries = Library.all().ancestor(library_key(libraryGroup_name))

   		if users.get_current_user() and is_admin_user:
   			registered_user_email = users.get_current_user().email()
   			loginout_url = users.create_logout_url('/')
   				   		
			template_values = {
				'funny_quote': funny_quote,
				'loginout_url': loginout_url,
				'loginout_linktext': loginout_linktext,
				'registered_user_email': registered_user_email,
				'is_admin_user': is_admin_user,
				'article_editors': article_editors,
				'libraries': libraries,
				}
			#with the data above, we now render the template and push it to the client
			
			template = jinja_environment.get_template('admin.html')
			self.response.out.write(template.render(template_values))
		else:
			test = self.redirect('/')

#these 'admin' functions could've been implemented as functions within AdminPage, but that would've been a more brittle solution (if request.path were misinterpreted, the system would fail to respond).

class AdminRemoveEditor(webapp2.RequestHandler):
	def post(self):
		key_string = self.request.get('removeEditor')
		editor = ArticleEditor.get(key_string)
		
		if users.get_current_user() and users.is_current_user_admin():
			if editor:
				editor.delete()

			self.redirect('/admin')
		else:
			self.redirect('/')

class AdminAddEditor(webapp2.RequestHandler):
	def post(self):
		articleEditorGroup_name = self.request.get('articleEditorGroup_name')
		article_editor = ArticleEditor(parent=articleEditor_key(articleEditorGroup_name))
		
		if users.get_current_user() and users.is_current_user_admin():
			article_editor.name = self.request.get('editorName')
			article_editor.title = self.request.get('editorTitle')
			article_editor.author = self.request.get('editorAuthor')
			article_editor.volume = self.request.get('editorVolume')
			article_editor.email = self.request.get('editorEmail')
			article_editor.execEditor = self.request.get('execEditor')
			article_editor.execEmail = self.request.get('execEmail')
			article_editor.put()

			self.redirect('/admin')
		else:
			self.redirect('/')

class AdminRemoveLibrary(webapp2.RequestHandler):
	def post(self):
		key_string = self.request.get('removeLibrary')
		library = Library.get(key_string)
		
		if users.get_current_user() and users.is_current_user_admin():
			if library:
				library.delete()

			self.redirect('/admin')
		else:
			self.redirect('/')

class AdminAddLibrary(webapp2.RequestHandler):
	def post(self):
		libraryGroup_name = self.request.get('articleEditorGroup_name')
		library = Library(parent=library_key(libraryGroup_name))
		
		if users.get_current_user() and users.is_current_user_admin():
			library.name = self.request.get('libraryName')
			library.put()

			self.redirect('/admin')
		else:
			self.redirect('/')

class AdminRemoveRequest(webapp2.RequestHandler):
	def post(self):
		key_string = self.request.get('requestKey')
		ill_request = ILLRequest.get(key_string)
		
		if users.get_current_user() and users.is_current_user_admin():
			search.Index(name=_INDEX_NAME).delete(key_string)
			if ill_request:
				ill_request.delete()
				#this is an ajax operation so no need to redirect on success
		else:
			self.redirect('/')

class AdminNotifyEditor(webapp2.RequestHandler):
	def post(self):
		key_string = self.request.get('notifyEditor')
		editor = ArticleEditor.get(key_string)
		
		if users.get_current_user() and users.is_current_user_admin():
			if editor:
				illrequestGroup_name = self.request.get('illrequestGroup_name')
				ready_to_return = ILLRequest.all().ancestor(illrequest_key(illrequestGroup_name))
				
				ready_to_return.filter("status =","received")
				ready_to_return.filter("articleEditorEmail =",editor.email)
				ready_to_return.filter("articleTitle =",editor.title)
				ready_to_return.order("library")
				
				return_list = "***sources to return***\r\r"
				
				for request in ready_to_return:
					return_list = return_list + request.title+" ("+request.resourceType+") at "+request.library+"\r\r"
				
				return_list = return_list + "***end of list***"
					
				mail.send_mail(sender=_ADMIN_ACCOUNT,to=editor.execEmail,subject="Sources to Return",body="""
				Howdy!  This is your friendly ILL Request System - the sources for your article can now be returned.  Here are the sources for """ + editor.title+"""!\r\r Drumroll please...\r\r"""+return_list)
				
				mail.send_mail(sender=_ADMIN_ACCOUNT,to=_ADMIN_ACCOUNT,subject="Notification Sent for Sources to Return",body="""
				From the News Desk of the ILL Request System: An email was sent to """+ editor.execEditor+""" working on the article  """ +editor.title+""" to return the following sources...\r\r"""+return_list)
				
			self.redirect('/admin')
		else:
			self.redirect('/')


class AdminGetRequestForm(webapp2.RequestHandler):
	def post(self):
		if users.get_current_user() and users.is_current_user_admin():
			key_string = self.request.get('requestKey')
			dismiss_edit_to = urllib.unquote(self.request.get('dismissEditTo'))
			ill_request = ILLRequest.get(key_string)
			is_admin_user = users.is_current_user_admin()
			
			articleEditorGroup_name = self.request.get('articleEditorGroup_name')
			article_editors = ArticleEditor.all().ancestor(articleEditor_key(articleEditorGroup_name))
			
			libraryGroup_name = self.request.get('libraryGroup_name')
			libraries = Library.all().ancestor(library_key(libraryGroup_name))
			
			form_handler_path = '/submit_request_edit'
			submit_message = 'Edit Request'

			if ill_request:
				template_values = {
					'ill_request_prefill': ill_request,
					'article_editors': article_editors,
					'libraries': libraries,
					'form_handler_path': form_handler_path,
					'is_admin_user': is_admin_user,
					'submit_message': submit_message,
					'dismiss_edit_to': dismiss_edit_to,
				}
				template = jinja_environment.get_template('request_form.html')
				self.response.out.write(template.render(template_values))
		else:
			self.redirect('/')
				
class AdminEditRequest(webapp2.RequestHandler):
	def post(self):
		if users.get_current_user() and users.is_current_user_admin():
			key_string = self.request.get('requestEditKey')
			illrequest = ILLRequest.get(key_string)
			if illrequest:
				# illrequest.requester = users.get_current_user().email() - this we don't want to change.
				illrequest.title = self.request.get('title')
				illrequest.author = self.request.get('author')
				illrequest.workEditor = self.request.get('workEditor')
				illrequest.publicationDate = illrequest.publicationDate.replace(year=int(self.request.get('pubYear')), month=int(self.request.get('pubMonth')), day=int(self.request.get('pubDay')))
				illrequest.volumeNumber = self.request.get('volumeNumber')
				illrequest.seriesName = self.request.get('seriesName')
				illrequest.pinCite = self.request.get('pinCite')
				illrequest.resourceType = self.request.get('resourceType')
				illrequest.description = self.request.get('description')
				article_editor = ArticleEditor.get(self.request.get('articleEditor'))
				illrequest.articleEditor = article_editor.name
				illrequest.articleEditorEmail = article_editor.email
				illrequest.execEditor = article_editor.execEditor
				illrequest.execEditorEmail = article_editor.execEmail
				illrequest.journalVolume = article_editor.volume
				illrequest.articleAuthor = article_editor.author
				illrequest.articleTitle = article_editor.title
				illrequest.fullCitation = self.request.get('fullCitation')
				illrequest.requesterFullName = self.request.get('requesterFullName')
				original_status = illrequest.status
				illrequest.status = self.request.get('status')
				if (original_status != 'received') and (illrequest.status == 'received'):
					mail.send_mail(sender=_ADMIN_ACCOUNT,to=illrequest.articleEditorEmail,subject="ILL Request In",body="""
					Howdy!  This is your friendly ILL Request System. Just a heads up that an interlibrary loan request for """+illrequest.title+""" for the """+illrequest.articleAuthor+""" article has been received and will soon be available.""")
					mail.send_mail(sender=_ADMIN_ACCOUNT,to=illrequest.requester,subject="ILL Request In",body="""
					Howdy!  This is your friendly ILL Request System. Just a heads up that your interlibrary loan request for """+illrequest.title+""" for the """+illrequest.articleAuthor+""" article has been received and will soon be available.""")
				if not illrequest.dueDate:
					illrequest.dueDate = datetime.datetime.today()
				illrequest.dueDate = illrequest.dueDate.replace(year=int(self.request.get('dueYear')), month=int(self.request.get('dueMonth')), day=int(self.request.get('dueDay')))
				illrequest.canRenew = self.request.get('canRenew')
				illrequest.modifiedBy.append(users.get_current_user().email())
				illrequest.modifiedOn.append(datetime.date.today())
				reason = self.request.get('modifiedWhy')
				if reason:
					illrequest.modifiedWhy.append(self.request.get('modifiedWhy'))
				else:
					illrequest.modifiedWhy.append("unspec.")
				
				illrequest.library = self.request.get('library')
				
					
				illrequest.put() #must come BEFORE we try to reference the key...
				illrequest.regenerate_search_document()
				
		self.redirect('/')

class RequestPage(webapp2.RequestHandler):
	def get(self):
		funny_quote = get_quote()
		loginout_url = None
		loginout_linktext = "logout"
		registered_user_email = None
		articleEditorGroup_name = self.request.get('articleEditorGroup_name')
		article_editors = ArticleEditor.all().ancestor(articleEditor_key(articleEditorGroup_name))
		is_admin_user = users.is_current_user_admin()
		form_handler_path = "/place_request"
		submit_message = "Place Request"
		
		if users.get_current_user():
			registered_user_email = users.get_current_user().email()
			loginout_url = users.create_logout_url('/')
			
			template_values = {
				'funny_quote': funny_quote,
				'loginout_url': loginout_url,
				'loginout_linktext':loginout_linktext,
				'registered_user_email': registered_user_email,
				'is_admin_user': is_admin_user,
				'article_editors':article_editors,
				'form_handler_path': form_handler_path,
				'submit_message': submit_message,
			}
			#with the data above, we now render the template and push it to the client
		
			template = jinja_environment.get_template('request.html')
			self.response.out.write(template.render(template_values))
		else:
			self.redirect('/')
	
	def post(self):
		illrequestGroup_name = self.request.get('illrequestGroup_name')
		illrequest = ILLRequest(parent=illrequest_key(illrequestGroup_name))
		
		if users.get_current_user():
			illrequest.requester = users.get_current_user().email()
			illrequest.title = self.request.get('title')
			illrequest.author = self.request.get('author')
			illrequest.workEditor = self.request.get('workEditor')
			illrequest.publicationDate = illrequest.publicationDate.replace(year=int(self.request.get('pubYear')), month=int(self.request.get('pubMonth')), day=int(self.request.get('pubDay')))
			illrequest.volumeNumber = self.request.get('volumeNumber')
			illrequest.seriesName = self.request.get('seriesName')
			illrequest.pinCite = self.request.get('pinCite')
			illrequest.resourceType = self.request.get('resourceType')
			illrequest.description = self.request.get('description')
			illrequest.requester = users.get_current_user().email()
			illrequest.requesterFullName = self.request.get('requesterFullName')
			article_editor = ArticleEditor.get(self.request.get('articleEditor'))
			illrequest.articleEditor = article_editor.name
			illrequest.articleEditorEmail = article_editor.email
			illrequest.execEditor = article_editor.execEditor
			illrequest.execEditorEmail = article_editor.execEmail
			illrequest.journalVolume = article_editor.volume
			illrequest.articleAuthor = article_editor.author
			illrequest.articleTitle = article_editor.title
			illrequest.fullCitation = self.request.get('fullCitation')
			illrequest.status = "unsent"
			illrequest.modifiedBy.append(illrequest.requester)
			illrequest.modifiedOn.append(datetime.date.today())
			illrequest.modifiedWhy.append('requested')
			#illrequest.requestedDate = (auto)
			#illrequest.dueDate = db.DateTimeProperty()
			#illrequest.canRenew = db.StringProperty()
			#illrequest.hasRenewed = db.BooleanProperty()
			#illrequest.modifiedBy = datetime.date
			#illrequest.modifiedOn = db.ListProperty(datetime.date,verbose_name=None,default=None)
	
			illrequest.put() #must come BEFORE we try to reference the key...
			illrequest.regenerate_search_document()
		
		self.redirect('/')

class QuoteSubmissionPage(webapp2.RequestHandler):
	def get(self):
		funny_quote = get_quote()
		loginout_url = None
		loginout_linktext = "logout"
		registered_user_email = None
		is_admin_user = users.is_current_user_admin()
		
		if users.get_current_user():
			registered_user_email = users.get_current_user().email()
			loginout_url = users.create_logout_url('/')
		
			template_values = {
				'funny_quote': funny_quote,
				'loginout_url': loginout_url,
				'loginout_linktext': loginout_linktext,
				'registered_user_email': registered_user_email,
				'is_admin_user': is_admin_user,
				}
			#with the data above, we now render the template and push it to the client
		
			template = jinja_environment.get_template('add_quote.html')
			self.response.out.write(template.render(template_values))
		else:
			self.redirect('/')

	def post(self):
		# We set the same parent key on the 'Greeting' to ensure each greeting is in
		# the same entity group. Queries across the single entity group will be
		# consistent. However, the write rate to a single entity group should
		# be limited to ~1/second.
		quoteGroup_name = self.request.get('quoteGroup_name')
		funny_quote = FunnyQuote(parent=quote_key(quoteGroup_name))
		
		if users.get_current_user():
			funny_quote.submitter = users.get_current_user().email()
			funny_quote.quote = self.request.get('quote')
			funny_quote.author = self.request.get('author')
			funny_quote.put()
	
		self.redirect('/')
		#self.redirect('/?' + urllib.urlencode({'quote_name': quote_name}))

class SearchPage(webapp2.RequestHandler):
	def get(self):
		funny_quote = get_quote()
		loginout_url = users.create_logout_url('/')
		loginout_linktext = "logout"
		registered_user_email = None
		is_admin_user = users.is_current_user_admin()
		
		if users.get_current_user():
			registered_user_email = users.get_current_user().email()
		
			template_values = {
				'funny_quote': funny_quote,
				'loginout_url': loginout_url,
				'loginout_linktext':loginout_linktext,
				'registered_user_email': registered_user_email,
				'is_admin_user': is_admin_user,
				}
	  	
			#with the data above, we now render the template and push it to the client
			template = jinja_environment.get_template('query.html')
			self.response.out.write(template.render(template_values))
			
		else:
			self.redirect('/')

	def post(self):
		registered_user_email = None
		loginout_linktext = "logout"
		loginout_url = None
		is_admin_user = users.is_current_user_admin()

		if users.get_current_user():
			funny_quote = get_quote()
			loginout_url = users.create_logout_url('/')
			registered_user_email = users.get_current_user().email()
			
			tried_to_search = True

			#build search the search
			
			key_list = []
			search_term = string.strip(self.request.get('search_string'))

			if search_term:

				query_string = self.request.get('search_type') + search_term
				logging.info(query_string)
								
				search_documents = search.Index(name=_INDEX_NAME).search(query_string)

				for result in search_documents:
					key_list.append(result.doc_id)
						
			search_results = ILLRequest.get(key_list)
			hit_count = len(search_results)
			
			template_values = {
				'funny_quote': funny_quote,
				'loginout_url': loginout_url,
				'loginout_linktext':loginout_linktext,
				'search_results': search_results,
				'hit_count':hit_count,
				'tried_to_search':tried_to_search,
				'registered_user_email': registered_user_email,
				'is_admin_user': is_admin_user,
				}
	
			#self.redirect('/')
			template = jinja_environment.get_template('query.html')
			self.response.out.write(template.render(template_values))
		else:
			self.redirect('/')

app = webapp2.WSGIApplication([('/', MainPage), ('/request', RequestPage), ('/place_request', RequestPage), ('/quote', QuoteSubmissionPage), ('/submit_quote', QuoteSubmissionPage), ('/search', SearchPage), ('/submit_search', SearchPage), ('/admin', AdminPage), ('/add_editor', AdminAddEditor), ('/remove_editor', AdminRemoveEditor), ('/add_library', AdminAddLibrary), ('/remove_library', AdminRemoveLibrary), ('/remove_request', AdminRemoveRequest), ('/edit_request', AdminGetRequestForm), ('/submit_request_edit', AdminEditRequest), ('/notify_editor_return', AdminNotifyEditor)],debug=True)
