#!/bin/python3

# NextCloud Mail Collector
# Author: LazyGatto
# Email: lazygatto@gmail.com
# GitHub URL: https://github.com/lazygatto/nextcloud-mail-collector
# Based on mail-attachments-archiver
# Author: Enrico Cambiaso
# Email: enrico.cambiaso[at]gmail.com
# GitHub project URL: https://github.com/auino/mail-attachments-archiver
#

# libraries import
import email, email.header, getpass, imaplib, os, time, re, requests
from requests.auth import HTTPBasicAuth

# --- --- --- --- ---
# CONFIGURATION BEGIN
# --- --- --- --- ---

# IMAP server connection configuration
USER = 'imap_email_user'
PWD = 'imap_password'
IMAPSERVER = 'imap_server'

# allowed senders list (may be configured separately for each directory)
MAIL1 = 'mail1@mail.domain'
MAIL2 = 'mail2@mail.domain'
MAIL3 = 'mail3@mail.domain'
MAIL4 = 'mail4@mail.domain'
MAIL5 = 'mail5@mail.domain'

# storage/archive capabilities configuration
MAIL_MAPPINGS = [
	{ 'filter_sender': True, 'senders': [ MAIL1 ], 'add_date': True, 'subject': [ '', 'SCAN' ], 'destination': '/opt/nextcloud_scripts/scan/' },
	{ 'filter_sender': True, 'senders': [ MAIL2 ], 'add_date': True, 'subject': [ '', 'SCAN' ], 'destination': '/opt/nextcloud_scripts/scan/' },
	{ 'filter_sender': True, 'senders': [ MAIL3 ], 'add_date': True, 'subject': [ '', 'TODO' ], 'destination': '/opt/nextcloud_scripts/scan/' },
	{ 'filter_sender': True, 'senders': [ MAIL4 ], 'add_date': True, 'subject': [ '', 'TODO' ], 'destination': '/opt/nextcloud_scripts/scan/' },
	{ 'filter_sender': True, 'senders': [ MAIL5 ], 'add_date': True, 'subject': [ '', 'TODO' ], 'destination': '/opt/nextcloud_scripts/scan/' },
]

# only consider unread emails?
FILTER_UNREAD_EMAILS = True

# mark emails as read after their attachments have been archived?
MARK_AS_READ = False

# delete emails after their attachments have been archived?
DELETE_EMAIL = True

# if no attachment is found, mark email as read?
MARK_AS_READ_NOATTACHMENTS = False

# if no attachment is found, delete email?
DELETE_EMAIL_NOATTACHMENTS = True

# if no match is found (on MAIL_MAPPINGS), mark email as read?
MARK_AS_READ_NOMATCH = True

# if no match is found (on MAIL_MAPPINGS), delete email?
DELETE_EMAIL_NOMATCH = True

# --- --- --- --- ---
# NEXTCLOUD CONFIGURATION PART
# --- --- --- --- ---

# This User must have rights to write into dirrectory you specified below
NC_USER = 'ncadmin'
NC_PASSWORD = 'user_password'
NC_SCHEME = 'http'
NC_HOST = '127.0.0.1'
NC_WEBDAV_PATH = 'remote.php/dav/files'
NC_FOLDER = 'SCANNER'

NC_WEBDAV_URL = NC_SCHEME+'://'+NC_HOST+'/'+NC_WEBDAV_PATH+'/'+NC_USER+'/'+NC_FOLDER

# if no file will be stored in filesystem permanently
DELETE_FILE_AFTER_UPLOAD = True

# --- --- --- --- ---
#  CONFIGURATION END
# --- --- --- --- ---

# source: https://stackoverflow.com/questions/12903893/python-imap-utf-8q-in-subject-string
def decode_mime_words(s): return u''.join(word.decode(encoding or 'utf8') if isinstance(word, bytes) else word for word, encoding in email.header.decode_header(s))

# connecting to the IMAP serer
m = imaplib.IMAP4_SSL(IMAPSERVER)
m.login(USER, PWD)
# use m.list() to get all the mailboxes
m.select("INBOX") # here you a can choose a mail box like INBOX instead

# you could filter using the IMAP rules here (check http://www.example-code.com/csharp/imap-search-critera.asp)
searchstring = 'ALL'
if FILTER_UNREAD_EMAILS: searchstring = 'UNSEEN'
resp, items = m.search(None, searchstring)
items = items[0].split() # getting the mails id
for emailid in items:
	# fetching the mail, "(RFC822)" means "get the whole stuff", but you can ask for headers only, etc
	resp, data = m.fetch(emailid, "(RFC822)")
	# getting the mail content
	email_body = data[0][1]
	# parsing the mail content to get a mail object
	mail = email.message_from_string(email_body.decode())
	# check if any attachments at all
	if mail.get_content_maintype() != 'multipart':
		emailid = str(emailid)
		# marking as read and delete, if necessary
		if MARK_AS_READ_NOATTACHMENTS: m.store(emailid,'+FLAGS','\Seen')
		if DELETE_EMAIL_NOATTACHMENTS: m.store(emailid,'+FLAGS','\\Deleted')
		continue
	# checking sender
	sender = mail['from'].split()[-1]
	senderaddress = re.sub(r'[<>]','', sender)
	print ("<"+str(mail['date'])+"> "+"["+str(mail['from'])+"] :"+str(mail['subject']))
	# check if subject is allowed
	subject = mail['subject']
	outputrule = None
	for el in MAIL_MAPPINGS:
		if el['filter_sender'] and (not (senderaddress.lower() in el['senders'])): continue
		for sj in el['subject']:
			if str(sj).lower() in str(subject).lower(): outputrule = el
	if outputrule == None: # no match is found
		# marking as read and delete, if necessary
		if MARK_AS_READ_NOMATCH: m.store(emailid,'+FLAGS','\Seen')
		if DELETE_EMAIL_NOMATCH: m.store(emailid,'+FLAGS','\\Deleted')
		continue
	outputdir = outputrule['destination']
	# we use walk to create a generator so we can iterate on the parts and forget about the recursive headach
	for part in mail.walk():
		# multipart are just containers, so we skip them
		if part.get_content_maintype() == 'multipart':
			#emailid = str(emailid)
			# marking as read and delete, if necessary
			if MARK_AS_READ: m.store(emailid,'+FLAGS','\Seen')
			if DELETE_EMAIL: m.store(emailid,'+FLAGS','\\Deleted')
			continue
		# is this part an attachment?
		if part.get('Content-Disposition') is None:
			# marking as read and delete, if necessary
			if MARK_AS_READ: m.store(emailid,'+FLAGS','\Seen')
			if DELETE_EMAIL: m.store(emailid,'+FLAGS','\Deleted')
			continue
		filename = part.get_filename()
		counter = 1
		# if there is no filename, we create one with a counter to avoid duplicates
		if not filename:
			filename = 'part-%03d%s' % (counter, 'bin')
			counter += 1
		# getting mail date
		if outputrule['add_date']:
			d = mail['Date']
			ss = [ ' +', ' -' ]
			for s in ss:
				if s in d: d = d.split(s)[0]
			maildate = time.strftime('%Y-%m-%d', time.strptime(d, '%a, %d %b %Y %H:%M:%S'))
			filename = maildate+'_'+filename
		filename = decode_mime_words(u''+filename)
		att_path = os.path.join(outputdir, filename)
		# check if output directory exists
		if not os.path.isdir(outputdir): os.makedirs(outputdir)
		# check if its already there
		if not os.path.isfile(att_path):
			try:
				print ('Saving to'+ str(att_path.encode('utf8'))) # Added .encode('utf8') to att_path
				# finally write the stuff
				fp = open(att_path, 'wb')
				fp.write(part.get_payload(decode=True))
				fp.close()

				file2upload = open(att_path,'rb')
				print ('Trying to put file into NextCloud')
				FILE_URL = NC_WEBDAV_URL+'/'+filename
				r = requests.put(FILE_URL, files={"archive": file2upload},auth = HTTPBasicAuth(NC_USER, NC_PASSWORD))

				if DELETE_FILE_AFTER_UPLOAD: os.remove(att_path)

				# marking as read and delete, if necessary
				if MARK_AS_READ: m.store(emailid,'+FLAGS','\Seen')
				if DELETE_EMAIL: m.store(emailid,'+FLAGS','\\Deleted')
			except: pass
# Expunge the items marked as deleted... (Otherwise it will never be actually deleted)
if DELETE_EMAIL: m.expunge()
# logout
m.logout()
