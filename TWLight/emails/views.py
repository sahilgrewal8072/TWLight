import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.mail import BadHeaderError, send_mail
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.generic.edit import FormView

from TWLight.emails.forms import ContactUsForm
from TWLight.emails.signals import ContactUs

@method_decorator(login_required, name='post')
class ContactUsView(FormView):
    template_name = 'emails/contact.html'
    form_class = ContactUsForm
    success_url = reverse_lazy('contact')

    def get_initial(self):
        initial = super(ContactUsView, self).get_initial()
        # @TODO: This sort of gets repeated in ContactUsForm.
        # We could probably be factored out to a common place for DRYness.
        if self.request.user.is_authenticated():
            if self.request.user.userprofile.use_wp_email:
                initial.update({
                     'email': self.request.user.email,
                })
        if ('message' in self.request.GET):
            initial.update({
                 'message': self.request.GET['message'],
            })
        initial.update({
            'next': reverse_lazy('contact'),
        })

        return initial

    def form_valid(self, form):
        # Adding an extra check to ensure the user is a wikipedia editor.
        try:
            assert self.request.user.editor
            
            email = form.cleaned_data['email']
            # Additional validation on the email field data
            # Regex from https://www.pythoncentral.io/how-to-validate-an-email-address-using-python/
            if re.match("^.+@([?)[a-zA-Z0-9-.]+.([a-zA-Z]{2,3}|[0-9]{1,3})(]?)$", email) != None:
                message = form.cleaned_data['message']
                ContactUs.new_email.send(
                    sender=self.__class__,
                    user_email=email,
                    editor_wp_username=self.request.user.editor.wp_username,
                    body=message
                )
                messages.add_message(self.request, messages.SUCCESS,
                # Translators: Shown to users when they successfully submit a new message using the contact us form.
                _('Your message has been sent. We\'ll get back to you soon!'))
            else:
                messages.add_message(self.request, messages.WARNING,
                # Translators: Shown to users when the email field of the contact us form contains an invalid email.
                _('The email entered is not valid. You can update your email <a href="{}">here</a>.'.format(reverse_lazy('users:email_change'))))
            
            return HttpResponseRedirect(reverse('contact'))
        except (AssertionError, AttributeError) as e:
            messages.add_message (self.request, messages.WARNING,
                # Translators: This message is shown to non-wikipedia editors who attempt to post data to the contact us form.
                _('You must be a Wikipedia editor to do that.'))
            raise PermissionDenied
        return self.request.user.editor