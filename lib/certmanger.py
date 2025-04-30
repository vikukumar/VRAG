from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import datetime
import ipaddress


class CertManger:

    passkey:str=''

    def __init__(self,*args, passkey:str='',**kwargs):
        if passkey:
            self.passkey = passkey
        pass

    @classmethod
    def set_passkey(self,passkey:str):
       self.passkey = passkey

    @classmethod
    def gen_CA(self,common_name:str, org_name:str,*args,country:str='IN',locality:str='Noida',state:str='UP',OrgUnit:str='IT',expire:int=10,alt_names:list[str]=[],**kwargs):
        pkey = rsa.generate_private_key(public_exponent=65537,key_size=2048,backend=default_backend())
        private_key = pkey.private_bytes(encoding=serialization.Encoding.PEM,format=serialization.PrivateFormat.PKCS8,encryption_algorithm=serialization.BestAvailableEncryption(self.passkey) if self.passkey else serialization.NoEncryption()).decode()

        serialNo = x509.random_serial_number()

        builder = x509.CertificateBuilder()
        builder = builder.subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, org_name),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, OrgUnit),
            x509.NameAttribute(NameOID.COUNTRY_NAME, country),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state),
            x509.NameAttribute(NameOID.LOCALITY_NAME, locality)
            ])).serial_number(serialNo)
        builder = builder.issuer_name(builder._subject_name)
        builder = builder.public_key(pkey.public_key())
        now = datetime.datetime.now(datetime.timezone.utc)
        builder = builder.not_valid_before(now)
        builder = builder.not_valid_after(now + datetime.timedelta(days=365 * expire))

        builder = builder.add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        if len(alt_names):
          san = x509.SubjectAlternativeName([x509.IPAddress(ipaddress.IPv4Address(n) if "." in n else ipaddress.IPv6Address(n)) if ("." in n and len(n.split(".")) == 4) or ":" in n else x509.DNSName(n) for n in alt_names])
          builder = builder.add_extension(san,critical=False)


        subject_key_identifier = x509.SubjectKeyIdentifier.from_public_key(pkey.public_key())
        
        # Authority Key Identifier links this certificate to the issuer's public key (self-signed in this case)
        authority_key_identifier = x509.AuthorityKeyIdentifier(
            key_identifier=subject_key_identifier.digest,
            authority_cert_issuer=[x509.DirectoryName(builder._subject_name)],
            authority_cert_serial_number=serialNo
        )

        builder = builder.add_extension(authority_key_identifier, critical=False)

        # Sign the certificate
        ca = builder.sign(
            private_key=pkey, algorithm=hashes.SHA256(),
            backend=default_backend()
        )

        cacert = ca.public_bytes(encoding=serialization.Encoding.PEM).decode()

        return private_key , cacert, serialNo
    

    @classmethod
    def gen_cert(self,CA:str,CA_Key:str,cname:str,org_name:str,*args,country:str='IN',locality:str='Noida',state:str='UP',OrgUnit:str='IT',alt_names:list[str]=[],expire:int=1,**kwargs):

        ca_key = serialization.load_pem_private_key(CA_Key.encode(), password=self.passkey if self.passkey else None,backend=default_backend())

        ca_cert = x509.load_pem_x509_certificate(CA.encode(),backend=default_backend())

        key = rsa.generate_private_key(public_exponent=65537,key_size=2048,backend=default_backend())

        private_key = key.private_bytes(encoding=serialization.Encoding.PEM,format=serialization.PrivateFormat.PKCS8,encryption_algorithm=serialization.BestAvailableEncryption(self.passkey) if self.passkey else serialization.NoEncryption()).decode()

        serialNo = x509.random_serial_number()

        builder = x509.CertificateBuilder()

        builder = builder.subject_name(x509.Name([
           x509.NameAttribute(NameOID.COMMON_NAME, cname),
           x509.NameAttribute(NameOID.ORGANIZATION_NAME, org_name),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, OrgUnit),
            x509.NameAttribute(NameOID.COUNTRY_NAME, country),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state),
            x509.NameAttribute(NameOID.LOCALITY_NAME, locality)
           ]))

        builder = builder.serial_number(serialNo)

        builder = builder.issuer_name(ca_cert.subject)

        builder = builder.public_key(key.public_key())
        now = datetime.datetime.now(datetime.timezone.utc)
        builder = builder.not_valid_before(now)
        builder = builder.not_valid_after(now + datetime.timedelta(days= 30 * expire))
        builder = builder.add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)

        if len(alt_names):
          names = [x509.IPAddress(ipaddress.IPv4Address(n) if "." in n else ipaddress.IPv6Address(n)) if ("." in n and len(n.split(".")) == 4) or ":" in n else x509.DNSName(n) for n in alt_names]
          builder = builder.add_extension(x509.SubjectAlternativeName(names),critical=False)


        subject_key_identifier = x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key())
        
        # Authority Key Identifier links this certificate to the issuer's public key (self-signed in this case)
        authority_key_identifier = x509.AuthorityKeyIdentifier(
            key_identifier=subject_key_identifier.digest,
            authority_cert_issuer=[x509.DirectoryName(builder._subject_name)],
            authority_cert_serial_number=serialNo
        )

        builder = builder.add_extension(authority_key_identifier, critical=False)

        certsing = builder.sign(
            private_key=ca_key, algorithm=hashes.SHA256(),
            backend=default_backend()
        )

        cert = certsing.public_bytes(encoding=serialization.Encoding.PEM).decode()

        return private_key, cert, serialNo

    @classmethod
    def auto_renew_CA(self,CA:str, Key:str,*args,**kwargs):
        ca_key = serialization.load_pem_private_key(Key.encode(), password=self.passkey if self.passkey else None,backend=default_backend())
        ca_cert = x509.load_pem_x509_certificate(CA.encode(),backend=default_backend())
        if not self.validateCert(ca_cert,ca_key):
          raise Exception("Invalid Certificate or Key")
        expire = ca_cert.not_valid_after_utc - ca_cert.not_valid_before_utc
        expire = expire.days
        serialNo = ca_cert.serial_number
        if ca_cert.not_valid_after_utc.timestamp() < datetime.datetime.now(datetime.timezone.utc).timestamp():
          pkey = rsa.generate_private_key(public_exponent=65537,key_size=2048,backend=default_backend())
          Key = pkey.private_bytes(encoding=serialization.Encoding.PEM,format=serialization.PrivateFormat.PKCS8,encryption_algorithm=serialization.BestAvailableEncryption(self.passkey) if self.passkey else serialization.NoEncryption()).decode()
          serialNo = x509.random_serial_number()
          builder = x509.CertificateBuilder()
          builder._subject_name = ca_cert.subject
          builder._extensions = ca_cert.extensions
          builder._issuer_name = ca_cert.issuer
          builder = builder.serial_number(serialNo)
          builder = builder.public_key(pkey.public_key())
          now = datetime.datetime.now(datetime.timezone.utc)
          builder = builder.not_valid_before(now)
          builder = builder.not_valid_after(now + datetime.timedelta(days=expire))
          ca = builder.sign(
            private_key=pkey, algorithm=hashes.SHA256(),
            backend=default_backend())
          CA = ca.public_bytes(encoding=serialization.Encoding.PEM).decode()
        return Key, CA, serialNo
    

    @classmethod
    def validateCert(self, cert, key, *args, **kwargs):
        if cert.public_key().public_numbers() == key.public_key().public_numbers():
            return True
        else:
           return False
        

    @classmethod
    def verifyCA(self, CA, cert,*args, **kwargs):
        try:
            CA.public_key().verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                cert.signature_hash_algorithm,
            )
            return True
        except Exception as e:
            print("Signature verification failed:", e)
            return False
    
    @classmethod
    def auto_renew_Cert(self,CA:str,CAKey:str, Cert:str, Key:str, *args, **kwargs):
        ca_cert = x509.load_pem_x509_certificate(CA.encode(),backend=default_backend())
        ca_key = serialization.load_pem_private_key(CAKey.encode(), password=self.passkey if self.passkey else None,backend=default_backend())
        pkey = serialization.load_pem_private_key(Key.encode(), password=self.passkey if self.passkey else None,backend=default_backend())
        cert = x509.load_pem_x509_certificate(Cert.encode(),backend=default_backend())
        if not self.validateCert(cert,pkey):
            raise Exception("Invalid Certificate or Key")
        if not self.verifyCA(ca_cert,cert):
           raise Exception("Invalid CA Certificate")
        expire = cert.not_valid_after_utc - cert.not_valid_before_utc
        expire = expire.days
        serialNo = cert.serial_number
        if cert.not_valid_after_utc.timestamp() < datetime.datetime.now(datetime.timezone.utc).timestamp():
            pkey = rsa.generate_private_key(public_exponent=65537,key_size=2048,backend=default_backend())
            Key = pkey.private_bytes(encoding=serialization.Encoding.PEM,format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.BestAvailableEncryption(self.passkey) if self.passkey else serialization. NoEncryption()).decode()
            serialNo = x509.random_serial_number()
            builder = x509.CertificateBuilder()
            builder._subject_name = cert.subject
            builder._extensions = ca_cert.extensions
            builder = builder.serial_number(serialNo)
            builder = builder.issuer_name(ca_cert.subject)
            builder = builder.public_key(pkey.public_key())
            now = datetime.datetime.now(datetime.timezone.utc)
            builder = builder.not_valid_before(now)
            builder = builder.not_valid_after(now + datetime.timedelta(days= expire))
            builder = builder.add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            certsing = builder.sign(
               private_key=ca_key, algorithm=hashes.SHA256(),
               backend=default_backend()
               )
            Cert = certsing.public_bytes(encoding=serialization.Encoding.PEM).decode()
        return Key, Cert, serialNo