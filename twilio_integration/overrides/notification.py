import frappe
from frappe import _
from frappe.email.doctype.notification.notification import Notification, get_context, json
from twilio_integration.twilio_integration.doctype.whatsapp_message.whatsapp_message import WhatsAppMessage
from twilio_integration.twilio_integration.utils import (get_media_public_url,delete_media_public_url)
from frappe.core.doctype.role.role import get_info_based_on_role
class SendNotification(Notification):
	def validate(self):
		self.validate_twilio_settings()

	def validate_twilio_settings(self):
		if self.enabled and self.channel == "WhatsApp" \
			and not frappe.db.get_single_value("Twilio Settings", "enabled"):
			frappe.throw(_("Please enable Twilio settings to send WhatsApp messages"))

	def send(self, doc):
		context = get_context(doc)
		context = {"doc": doc, "alert": self, "comments": None}
		if doc.get("_comments"):
			context["comments"] = json.loads(doc.get("_comments"))

		if self.is_standard:
			self.load_standard_properties(context)

		try:
			if self.channel == 'WhatsApp':
				self.send_whatsapp_msg(doc, context)
		except:
			frappe.log_error(title='Failed to send notification', message=frappe.get_traceback())

		super(SendNotification, self).send(doc)

	def get_whatsapp_receiver_list(self, doc, context):
		"""return receiver list based on the doc field and role specified"""
		print('FUNCTION CALLED')
		receiver_list = []
		for recipient in self.recipients:
			if recipient.condition:
				if not frappe.safe_eval(recipient.condition, None, context):
					continue
			# Get DocField Properties
			docfield_list = [field for field in frappe.get_doc('DocType',doc.doctype).fields if field.fieldname == recipient.receiver_by_document_field]
			docfield = docfield_list[0] if len(docfield_list) > 0 else None
			print(f"\n\n\n{docfield}\n\n\n	")
			# For sending messages to the owner's mobile phone number
			if recipient.receiver_by_document_field == "doc_owner":
				receiver_list += frappe.db.get_value('User',doc.get('owner'),'mobile_no')
			# For sending messages to the number specified in the receiver field
			elif docfield:
				if docfield.fieldtype == 'Link':
					if docfield.options == 'User':
						receiver_list.append(frappe.db.get_value('User',doc.get(docfield.fieldname),'mobile_no'))
					elif docfield.options == 'Employee':
						receiver_list.append(frappe.db.get_value('Employee',doc.get(docfield.fieldname),'cell_number'))
					elif docfield.options == 'Contact':
						receiver_list.append(frappe.db.get_value('Contact',doc.get(docfield.fieldname),'mobile_no'))
				elif docfield.fieldtype == 'Data' and docfield.options == 'Phone':
					receiver_list.append(doc.get(docfield.fieldname))

			# For sending messages to specified role
			if recipient.receiver_by_role:
				receiver_list += get_info_based_on_role(recipient.receiver_by_role, "mobile_no")
		return receiver_list

	
	def send_whatsapp_msg(self, doc, context):
		media_url = get_media_public_url(
			doctype = doc.doctype,
			docname = doc.name,
			print_format = self.print_format if self.print_format else None,
			print_letterhead = True
			)
		reclist = []
		try:
			reclist = self.get_whatsapp_receiver_list(doc,context)
			print(f'{reclist}')
		except:
			print('Error Occurred')
		print('\n\n\n\nCatchin Errors\n\n\n\n')
		WhatsAppMessage.send_whatsapp_message(
			receiver_list=self.get_whatsapp_receiver_list(doc, context),
			message=frappe.render_template(self.message, context),
			doctype = self.doctype,
			docname = self.name,
			media=media_url
		)
		delete_media_public_url(media_url)