# -*- coding: utf-8 -*-

# Copyright (c) 2010-2021 OneLogin, Inc.
# MIT License

import json
from os.path import dirname, join, exists
import unittest
from urlparse import urlparse, parse_qs
from xml.dom.minidom import parseString

from onelogin.saml2.constants import OneLogin_Saml2_Constants
from onelogin.saml2.logout_response import OneLogin_Saml2_Logout_Response
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils
from onelogin.saml2.errors import OneLogin_Saml2_ValidationError


class OneLogin_Saml2_Logout_Response_Test(unittest.TestCase):
    data_path = join(dirname(dirname(dirname(dirname(__file__)))), 'data')
    settings_path = join(dirname(dirname(dirname(dirname(__file__)))), 'settings')

    def loadSettingsJSON(self, name='settings1.json'):
        filename = join(self.settings_path, name)
        if exists(filename):
            stream = open(filename, 'r')
            settings = json.load(stream)
            stream.close()
            return settings

    def file_contents(self, filename):
        f = open(filename, 'r')
        content = f.read()
        f.close()
        return content

    def testConstructor(self):
        """
        Tests the OneLogin_Saml2_LogoutResponse Constructor.
        """
        settings = OneLogin_Saml2_Settings(self.loadSettingsJSON())
        message = self.file_contents(join(self.data_path, 'logout_responses', 'logout_response_deflated.xml.base64'))
        response = OneLogin_Saml2_Logout_Response(settings, message)
        self.assertRegexpMatches(response.document.toxml(), '<samlp:LogoutResponse')

    def testCreateDeflatedSAMLLogoutResponseURLParameter(self):
        """
        Tests the OneLogin_Saml2_LogoutResponse Constructor.
        The creation of a deflated SAML Logout Response
        """
        settings = OneLogin_Saml2_Settings(self.loadSettingsJSON())
        in_response_to = 'ONELOGIN_21584ccdfaca36a145ae990442dcd96bfe60151e'
        response_builder = OneLogin_Saml2_Logout_Response(settings)
        response_builder.build(in_response_to)
        parameters = {'SAMLResponse': response_builder.get_response()}

        logout_url = OneLogin_Saml2_Utils.redirect('http://idp.example.com/SingleLogoutService.php', parameters, True)

        self.assertRegexpMatches(logout_url, r'^http://idp\.example\.com\/SingleLogoutService\.php\?SAMLResponse=')
        url_parts = urlparse(logout_url)
        exploded = parse_qs(url_parts.query)
        inflated = OneLogin_Saml2_Utils.decode_base64_and_inflate(exploded['SAMLResponse'][0])
        self.assertRegexpMatches(inflated, '^<samlp:LogoutResponse')

    def testGetStatus(self):
        """
        Tests the get_status method of the OneLogin_Saml2_LogoutResponse
        """
        settings = OneLogin_Saml2_Settings(self.loadSettingsJSON())
        message = self.file_contents(join(self.data_path, 'logout_responses', 'logout_response_deflated.xml.base64'))
        response = OneLogin_Saml2_Logout_Response(settings, message)
        status = response.get_status()
        self.assertEquals(status, OneLogin_Saml2_Constants.STATUS_SUCCESS)

        dom = parseString(OneLogin_Saml2_Utils.decode_base64_and_inflate(message))
        status_code_node = dom.getElementsByTagName('samlp:StatusCode')[0]
        status_code_node.parentNode.removeChild(status_code_node)
        xml = dom.toxml()
        message_2 = OneLogin_Saml2_Utils.deflate_and_base64_encode(xml)
        response_2 = OneLogin_Saml2_Logout_Response(settings, message_2)
        self.assertIsNone(response_2.get_status())

    def testGetIssuer(self):
        """
        Tests the get_issuer of the OneLogin_Saml2_LogoutResponse
        """
        settings = OneLogin_Saml2_Settings(self.loadSettingsJSON())
        message = self.file_contents(join(self.data_path, 'logout_responses', 'logout_response_deflated.xml.base64'))
        response = OneLogin_Saml2_Logout_Response(settings, message)

        issuer = response.get_issuer()
        self.assertEquals('http://idp.example.com/', issuer)

        dom = parseString(OneLogin_Saml2_Utils.decode_base64_and_inflate(message))
        issuer_node = dom.getElementsByTagName('saml:Issuer')[0]
        issuer_node.parentNode.removeChild(issuer_node)
        xml = dom.toxml()
        message_2 = OneLogin_Saml2_Utils.deflate_and_base64_encode(xml)
        response_2 = OneLogin_Saml2_Logout_Response(settings, message_2)
        issuer_2 = response_2.get_issuer()
        self.assertIsNone(issuer_2)

    def testQuery(self):
        """
        Tests the private method __query of the OneLogin_Saml2_LogoutResponse
        """
        settings = OneLogin_Saml2_Settings(self.loadSettingsJSON())
        message = self.file_contents(join(self.data_path, 'logout_responses', 'logout_response_deflated.xml.base64'))
        response = OneLogin_Saml2_Logout_Response(settings, message)

        issuer = response.get_issuer()
        self.assertEquals('http://idp.example.com/', issuer)

    def testIsInvalidXML(self):
        """
        Tests the is_valid method of the OneLogin_Saml2_LogoutResponse
        Case Invalid XML
        """
        message = OneLogin_Saml2_Utils.deflate_and_base64_encode('<xml>invalid</xml>')
        request_data = {
            'http_host': 'example.com',
            'script_name': 'index.html',
            'get_data': {}
        }
        settings = OneLogin_Saml2_Settings(self.loadSettingsJSON())

        response = OneLogin_Saml2_Logout_Response(settings, message)
        self.assertTrue(response.is_valid(request_data))

        settings.set_strict(True)
        response_2 = OneLogin_Saml2_Logout_Response(settings, message)
        self.assertFalse(response_2.is_valid(request_data))

    def testIsInValidRequestId(self):
        """
        Tests the is_valid method of the OneLogin_Saml2_LogoutResponse
        Case invalid request Id
        """
        request_data = {
            'http_host': 'example.com',
            'script_name': 'index.html',
            'get_data': {}
        }
        settings = OneLogin_Saml2_Settings(self.loadSettingsJSON())
        message = self.file_contents(join(self.data_path, 'logout_responses', 'logout_response_deflated.xml.base64'))

        plain_message = OneLogin_Saml2_Utils.decode_base64_and_inflate(message)
        current_url = OneLogin_Saml2_Utils.get_self_url_no_query(request_data)
        plain_message = plain_message.replace('http://stuff.com/endpoints/endpoints/sls.php', current_url)
        message = OneLogin_Saml2_Utils.deflate_and_base64_encode(plain_message)

        request_id = 'invalid_request_id'

        settings.set_strict(False)
        response = OneLogin_Saml2_Logout_Response(settings, message)
        self.assertTrue(response.is_valid(request_data, request_id))

        settings.set_strict(True)
        response_2 = OneLogin_Saml2_Logout_Response(settings, message)
        self.assertFalse(response_2.is_valid(request_data, request_id))
        self.assertIn('The InResponseTo of the Logout Response:', response_2.get_error())

    def testIsInValidIssuer(self):
        """
        Tests the is_valid method of the OneLogin_Saml2_LogoutResponse
        Case invalid Issuer
        """
        request_data = {
            'http_host': 'example.com',
            'script_name': 'index.html',
            'get_data': {}
        }
        settings = OneLogin_Saml2_Settings(self.loadSettingsJSON())
        message = self.file_contents(join(self.data_path, 'logout_responses', 'logout_response_deflated.xml.base64'))

        plain_message = OneLogin_Saml2_Utils.decode_base64_and_inflate(message)
        current_url = OneLogin_Saml2_Utils.get_self_url_no_query(request_data)
        plain_message = plain_message.replace('http://stuff.com/endpoints/endpoints/sls.php', current_url)
        plain_message = plain_message.replace('http://idp.example.com/', 'http://invalid.issuer.example.com')
        message = OneLogin_Saml2_Utils.deflate_and_base64_encode(plain_message)

        settings.set_strict(False)
        response = OneLogin_Saml2_Logout_Response(settings, message)
        self.assertTrue(response.is_valid(request_data))

        settings.set_strict(True)
        response_2 = OneLogin_Saml2_Logout_Response(settings, message)
        self.assertFalse(response_2.is_valid(request_data))
        self.assertIn('Invalid issuer in the Logout Response', response_2.get_error())

    def testIsInValidDestination(self):
        """
        Tests the is_valid method of the OneLogin_Saml2_LogoutResponse
        Case invalid Destination
        """
        request_data = {
            'http_host': 'example.com',
            'script_name': 'index.html',
            'get_data': {}
        }
        settings = OneLogin_Saml2_Settings(self.loadSettingsJSON())
        message = self.file_contents(join(self.data_path, 'logout_responses', 'logout_response_deflated.xml.base64'))

        settings.set_strict(False)
        response = OneLogin_Saml2_Logout_Response(settings, message)
        self.assertTrue(response.is_valid(request_data))

        settings.set_strict(True)
        response_2 = OneLogin_Saml2_Logout_Response(settings, message)
        self.assertFalse(response_2.is_valid(request_data))
        self.assertIn('The LogoutResponse was received at', response_2.get_error())

        # Empty destination
        dom = parseString(OneLogin_Saml2_Utils.decode_base64_and_inflate(message))
        dom.firstChild.setAttribute('Destination', '')
        xml = dom.toxml()
        message_3 = OneLogin_Saml2_Utils.deflate_and_base64_encode(xml)
        response_3 = OneLogin_Saml2_Logout_Response(settings, message_3)
        self.assertTrue(response_3.is_valid(request_data))

        # No destination
        dom.firstChild.removeAttribute('Destination')
        xml = dom.toxml()
        message_4 = OneLogin_Saml2_Utils.deflate_and_base64_encode(xml)
        response_4 = OneLogin_Saml2_Logout_Response(settings, message_4)
        self.assertTrue(response_4.is_valid(request_data))

    def testIsValidWithCapitalization(self):
        """
        Tests the is_valid method of the OneLogin_Saml2_LogoutResponse
        """
        request_data = {
            'http_host': 'exaMPLe.com',
            'script_name': 'index.html',
            'get_data': {}
        }
        settings = OneLogin_Saml2_Settings(self.loadSettingsJSON())
        message = self.file_contents(join(self.data_path, 'logout_responses', 'logout_response_deflated.xml.base64'))

        response = OneLogin_Saml2_Logout_Response(settings, message)
        self.assertTrue(response.is_valid(request_data))

        settings.set_strict(True)
        response_2 = OneLogin_Saml2_Logout_Response(settings, message)
        with self.assertRaisesRegexp(Exception, 'The LogoutResponse was received at'):
            response_2.is_valid(request_data, raise_exceptions=True)

        plain_message = OneLogin_Saml2_Utils.decode_base64_and_inflate(message)
        current_url = OneLogin_Saml2_Utils.get_self_url_no_query(request_data).lower()
        plain_message = plain_message.replace('http://stuff.com/endpoints/endpoints/sls.php', current_url)
        message_3 = OneLogin_Saml2_Utils.deflate_and_base64_encode(plain_message)

        response_3 = OneLogin_Saml2_Logout_Response(settings, message_3)
        self.assertTrue(response_3.is_valid(request_data))

    def testIsInValidWithCapitalization(self):
        """
        Tests the is_valid method of the OneLogin_Saml2_LogoutResponse
        """
        request_data = {
            'http_host': 'example.com',
            'script_name': 'INdex.html',
            'get_data': {}
        }
        settings = OneLogin_Saml2_Settings(self.loadSettingsJSON())
        message = self.file_contents(join(self.data_path, 'logout_responses', 'logout_response_deflated.xml.base64'))

        response = OneLogin_Saml2_Logout_Response(settings, message)
        self.assertTrue(response.is_valid(request_data))

        settings.set_strict(True)
        response_2 = OneLogin_Saml2_Logout_Response(settings, message)
        with self.assertRaisesRegexp(Exception, 'The LogoutResponse was received at'):
            response_2.is_valid(request_data, raise_exceptions=True)

        plain_message = OneLogin_Saml2_Utils.decode_base64_and_inflate(message)
        current_url = OneLogin_Saml2_Utils.get_self_url_no_query(request_data).lower()
        plain_message = plain_message.replace('http://stuff.com/endpoints/endpoints/sls.php', current_url)
        message_3 = OneLogin_Saml2_Utils.deflate_and_base64_encode(plain_message)

        response_3 = OneLogin_Saml2_Logout_Response(settings, message_3)
        self.assertFalse(response_3.is_valid(request_data))

    def testIsValidRaisesExceptionWhenRaisesArgumentIsTrue(self):
        message = OneLogin_Saml2_Utils.deflate_and_base64_encode('<xml>invalid</xml>')
        request_data = {
            'http_host': 'example.com',
            'script_name': 'index.html',
            'get_data': {}
        }
        settings = OneLogin_Saml2_Settings(self.loadSettingsJSON())
        settings.set_strict(True)

        response = OneLogin_Saml2_Logout_Response(settings, message)

        self.assertFalse(response.is_valid(request_data))

        with self.assertRaisesRegexp(OneLogin_Saml2_ValidationError, "Invalid SAML Logout Response. Not match the saml-schema-protocol-2.0.xsd"):
            response.is_valid(request_data, raise_exceptions=True)

    def testIsInValidSign(self):
        """
        Tests the is_valid method of the OneLogin_Saml2_LogoutResponse
        """
        request_data = {
            'http_host': 'example.com',
            'script_name': 'index.html',
            'get_data': {}
        }
        settings = OneLogin_Saml2_Settings(self.loadSettingsJSON())

        settings.set_strict(False)
        request_data['get_data'] = {
            'SAMLResponse': 'fZJva8IwEMa/Ssl7TZrW/gnqGHMMwSlM8cXeyLU9NaxNQi9lfvxVZczB5ptwSe733MPdjQma2qmFPdjOvyE5awiDU1MbUpevCetaoyyQJmWgQVK+VOvH14WSQ6Fca70tbc1ukPsEEGHrtTUsmM8mbDfKUhnFci8gliGINI/yXIAAiYnsw6JIRgWWAKlkwRZb6skJ64V6nKjDuSEPxvdPIowHIhpIsQkTFaYqSt9ZMEPy2oC/UEfvHSnOnfZFV38MjR1oN7TtgRv8tAZre9CGV9jYkGtT4Wnoju6Bauprme/ebOyErZbPi9XLfLnDoohwhHGc5WVSVhjCKM6rBMpYQpWJrIizfZ4IZNPxuTPqYrmd/m+EdONqPOfy8yG5rhxv0EMFHs52xvxWaHyd3tqD7+j37clWGGyh7vD+POiSrdZdWSIR49NrhR9R/teGTL8A',
            'RelayState': 'https://pitbulk.no-ip.org/newonelogin/demo1/index.php',
            'SigAlg': 'http://www.w3.org/2000/09/xmldsig#rsa-sha1',
            'Signature': 'vfWbbc47PkP3ejx4bjKsRX7lo9Ml1WRoE5J5owF/0mnyKHfSY6XbhO1wwjBV5vWdrUVX+xp6slHyAf4YoAsXFS0qhan6txDiZY4Oec6yE+l10iZbzvie06I4GPak4QrQ4gAyXOSzwCrRmJu4gnpeUxZ6IqKtdrKfAYRAcVfNKGA='
        }
        response = OneLogin_Saml2_Logout_Response(settings, request_data['get_data']['SAMLResponse'])
        self.assertTrue(response.is_valid(request_data))

        relayState = request_data['get_data']['RelayState']
        del request_data['get_data']['RelayState']
        inv_response = OneLogin_Saml2_Logout_Response(settings, request_data['get_data']['SAMLResponse'])
        self.assertFalse(inv_response.is_valid(request_data))
        request_data['get_data']['RelayState'] = relayState

        settings.set_strict(True)
        response_2 = OneLogin_Saml2_Logout_Response(settings, request_data['get_data']['SAMLResponse'])
        self.assertFalse(response_2.is_valid(request_data))
        self.assertIn('Invalid issuer in the Logout Response', response_2.get_error())

        settings.set_strict(False)
        old_signature = request_data['get_data']['Signature']
        request_data['get_data']['Signature'] = 'vfWbbc47PkP3ejx4bjKsRX7lo9Ml1WRoE5J5owF/0mnyKHfSY6XbhO1wwjBV5vWdrUVX+xp6slHyAf4YoAsXFS0qhan6txDiZY4Oec6yE+l10iZbzvie06I4GPak4QrQ4gAyXOSzwCrRmJu4gnpeUxZ6IqKtdrKfAYRAcVf3333='
        response_3 = OneLogin_Saml2_Logout_Response(settings, request_data['get_data']['SAMLResponse'])
        self.assertFalse(response_3.is_valid(request_data))
        self.assertIn('Signature validation failed. Logout Response rejected', response_3.get_error())

        request_data['get_data']['Signature'] = old_signature
        old_signature_algorithm = request_data['get_data']['SigAlg']
        del request_data['get_data']['SigAlg']
        response_4 = OneLogin_Saml2_Logout_Response(settings, request_data['get_data']['SAMLResponse'])
        self.assertTrue(response_4.is_valid(request_data))

        request_data['get_data']['RelayState'] = 'http://example.com/relaystate'
        response_5 = OneLogin_Saml2_Logout_Response(settings, request_data['get_data']['SAMLResponse'])
        self.assertFalse(response_5.is_valid(request_data))
        self.assertIn('Signature validation failed. Logout Response rejected', response_5.get_error())

        settings.set_strict(True)
        current_url = OneLogin_Saml2_Utils.get_self_url_no_query(request_data)
        plain_message_6 = OneLogin_Saml2_Utils.decode_base64_and_inflate(request_data['get_data']['SAMLResponse'])
        plain_message_6 = plain_message_6.replace('https://pitbulk.no-ip.org/newonelogin/demo1/index.php?sls', current_url)
        plain_message_6 = plain_message_6.replace('https://pitbulk.no-ip.org/simplesaml/saml2/idp/metadata.php', 'http://idp.example.com/')
        request_data['get_data']['SAMLResponse'] = OneLogin_Saml2_Utils.deflate_and_base64_encode(plain_message_6)

        response_6 = OneLogin_Saml2_Logout_Response(settings, request_data['get_data']['SAMLResponse'])
        self.assertFalse(response_6.is_valid(request_data))
        self.assertIn('Signature validation failed. Logout Response rejected', response_6.get_error())

        settings.set_strict(False)
        response_7 = OneLogin_Saml2_Logout_Response(settings, request_data['get_data']['SAMLResponse'])
        self.assertFalse(response_7.is_valid(request_data))
        self.assertIn('Signature validation failed. Logout Response rejected', response_7.get_error())

        request_data['get_data']['SigAlg'] = 'http://www.w3.org/2000/09/xmldsig#dsa-sha1'
        response_8 = OneLogin_Saml2_Logout_Response(settings, request_data['get_data']['SAMLResponse'])
        self.assertFalse(response_8.is_valid(request_data))
        self.assertIn('Signature validation failed. Logout Response rejected', response_8.get_error())

        settings_info = self.loadSettingsJSON()
        settings_info['strict'] = True
        settings_info['security']['wantMessagesSigned'] = True
        settings = OneLogin_Saml2_Settings(settings_info)

        request_data['get_data']['SigAlg'] = old_signature_algorithm
        old_signature = request_data['get_data']['Signature']
        del request_data['get_data']['Signature']
        request_data['get_data']['SAMLResponse'] = OneLogin_Saml2_Utils.deflate_and_base64_encode(plain_message_6)
        response_9 = OneLogin_Saml2_Logout_Response(settings, request_data['get_data']['SAMLResponse'])
        self.assertFalse(response_9.is_valid(request_data))
        self.assertIn('The Message of the Logout Response is not signed and the SP require it', response_9.get_error())

        request_data['get_data']['Signature'] = old_signature
        settings_info['idp']['certFingerprint'] = 'afe71c28ef740bc87425be13a2263d37971da1f9'
        del settings_info['idp']['x509cert']
        settings_2 = OneLogin_Saml2_Settings(settings_info)

        response_10 = OneLogin_Saml2_Logout_Response(settings_2, request_data['get_data']['SAMLResponse'])
        self.assertFalse(response_10.is_valid(request_data))
        self.assertIn('In order to validate the sign on the Logout Response, the x509cert of the IdP is required', response_10.get_error())

    def testIsValid(self):
        """
        Tests the is_valid method of the OneLogin_Saml2_LogoutResponse
        """
        request_data = {
            'http_host': 'example.com',
            'script_name': 'index.html',
            'get_data': {}
        }
        settings = OneLogin_Saml2_Settings(self.loadSettingsJSON())
        message = self.file_contents(join(self.data_path, 'logout_responses', 'logout_response_deflated.xml.base64'))

        response = OneLogin_Saml2_Logout_Response(settings, message)
        self.assertTrue(response.is_valid(request_data))

        settings.set_strict(True)
        response_2 = OneLogin_Saml2_Logout_Response(settings, message)
        self.assertFalse(response_2.is_valid(request_data))
        self.assertIn('The LogoutResponse was received at', response_2.get_error())

        plain_message = OneLogin_Saml2_Utils.decode_base64_and_inflate(message)
        current_url = OneLogin_Saml2_Utils.get_self_url_no_query(request_data)
        plain_message = plain_message.replace('http://stuff.com/endpoints/endpoints/sls.php', current_url)
        message_3 = OneLogin_Saml2_Utils.deflate_and_base64_encode(plain_message)

        response_3 = OneLogin_Saml2_Logout_Response(settings, message_3)
        self.assertTrue(response_3.is_valid(request_data))

    def testIsValidSignUsingX509certMulti(self):
        """
        Tests the is_valid method of the OneLogin_Saml2_LogoutResponse
        """
        request_data = {
            'http_host': 'example.com',
            'script_name': 'index.html',
            'get_data': {
                'SAMLResponse': 'fZHbasJAEIZfJey9ZrNZc1gSodRSBKtQxYveyGQz1kCyu2Q24OM3jS21UHo3p++f4Z+CoGud2th3O/hXJGcNYXDtWkNqapVs6I2yQA0pAx2S8lrtH142Ssy5cr31VtuW3SH/E0CEvW+sYcF6VbLTIktFLMWZgxQR8DSP85wDB4GJGMOqShYVaoBUsOCIPY1kyUahEScacG3Ig/FjiUdyxuOZ4IcoUVGq4vSNBSsk3xjwE3Xx3qkwJD+cz3NtuxBN7WxjPN1F1NLcXdwob77tONiS7bZPm93zenvCqopxgVJmuU50jREsZF4noKWAOuNZJbNznnBky+LTDDVd2S+/dje1m+MVOtfidEER3g8Vt2fsPfiBfmePtsbgCO2A/9tL07TaD1ojEQuXtw0/ouFfD19+AA==',
                'RelayState': 'http://stuff.com/endpoints/endpoints/index.php',
                'SigAlg': 'http://www.w3.org/2000/09/xmldsig#rsa-sha1',
                'Signature': 'OV9c4R0COSjN69fAKCpV7Uj/yx6/KFxvbluVCzdK3UuortpNMpgHFF2wYNlMSG9GcYGk6p3I8nB7Z+1TQchMWZOlO/StjAqgtZhtpiwPcWryNuq8vm/6hnJ3zMDhHTS7F8KG4qkCXmJ9sQD3Y31UNcuygBwIbNakvhDT5Qo9Nsw='
            }
        }
        settings_info = self.loadSettingsJSON('settings8.json')
        settings_info['strict'] = False
        settings = OneLogin_Saml2_Settings(settings_info)
        logout_response = OneLogin_Saml2_Logout_Response(settings, request_data['get_data']['SAMLResponse'])
        self.assertTrue(logout_response.is_valid(request_data))

    def testIsInValidRejectingDeprecatedSignatureAlgorithm(self):
        """
        Tests the is_valid method of the OneLogin_Saml2_LogoutResponse
        """
        """
        Tests the is_valid method of the OneLogin_Saml2_LogoutResponse
        """
        request_data = {
            'http_host': 'example.com',
            'script_name': 'index.html',
            'get_data': {
                'SAMLResponse': 'fZHbasJAEIZfJey9ZrNZc1gSodRSBKtQxYveyGQz1kCyu2Q24OM3jS21UHo3p++f4Z+CoGud2th3O/hXJGcNYXDtWkNqapVs6I2yQA0pAx2S8lrtH142Ssy5cr31VtuW3SH/E0CEvW+sYcF6VbLTIktFLMWZgxQR8DSP85wDB4GJGMOqShYVaoBUsOCIPY1kyUahEScacG3Ig/FjiUdyxuOZ4IcoUVGq4vSNBSsk3xjwE3Xx3qkwJD+cz3NtuxBN7WxjPN1F1NLcXdwob77tONiS7bZPm93zenvCqopxgVJmuU50jREsZF4noKWAOuNZJbNznnBky+LTDDVd2S+/dje1m+MVOtfidEER3g8Vt2fsPfiBfmePtsbgCO2A/9tL07TaD1ojEQuXtw0/ouFfD19+AA==',
                'RelayState': 'http://stuff.com/endpoints/endpoints/index.php',
                'SigAlg': 'http://www.w3.org/2000/09/xmldsig#rsa-sha1',
                'Signature': 'OV9c4R0COSjN69fAKCpV7Uj/yx6/KFxvbluVCzdK3UuortpNMpgHFF2wYNlMSG9GcYGk6p3I8nB7Z+1TQchMWZOlO/StjAqgtZhtpiwPcWryNuq8vm/6hnJ3zMDhHTS7F8KG4qkCXmJ9sQD3Y31UNcuygBwIbNakvhDT5Qo9Nsw='
            }
        }
        settings_info = self.loadSettingsJSON('settings8.json')
        settings_info['security']['rejectDeprecatedAlgorithm'] = True
        settings = OneLogin_Saml2_Settings(settings_info)
        logout_response = OneLogin_Saml2_Logout_Response(settings, request_data['get_data']['SAMLResponse'])
        self.assertFalse(logout_response.is_valid(request_data))
        self.assertEqual('Deprecated signature algorithm found: http://www.w3.org/2000/09/xmldsig#rsa-sha1', logout_response.get_error())

    def testGetXML(self):
        """
        Tests that we can get the logout response XML directly without
        going through intermediate steps
        """
        response = self.file_contents(join(self.data_path, 'logout_responses', 'logout_response.xml'))
        settings = OneLogin_Saml2_Settings(self.loadSettingsJSON())

        logout_response_generated = OneLogin_Saml2_Logout_Response(settings)
        logout_response_generated.build("InResponseValue")

        expectedFragment = (
            'Destination="http://idp.example.com/SingleLogoutService.php"\n'
            '                      InResponseTo="InResponseValue"\n>\n'
            '    <saml:Issuer>http://stuff.com/endpoints/metadata.php</saml:Issuer>\n'
            '    <samlp:Status>\n'
            '        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success" />\n'
            '    </samlp:Status>\n'
            '</samlp:LogoutResponse>'
        )
        self.assertIn(expectedFragment, logout_response_generated.get_xml())

        logout_response_processed = OneLogin_Saml2_Logout_Response(settings, OneLogin_Saml2_Utils.deflate_and_base64_encode(response))
        self.assertEqual(response, logout_response_processed.get_xml())


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    unittest.main(testRunner=runner)
