# PhishFarm
A tool that facilitates development of phishing pages for blue teams

# Cloning
PhishFarm.py is implemented as a mitmproxy [https://github.com/mitmproxy/mitmproxy] addon. It requires one additional command line option: --set clonedomain=TARGET_DOMAIN

After the start of the mitmproxy PhishFarm addon will prompt a set of credentials that should be used for authentication. These random credentials are used to automatically create parameter extraction rules [siteclone.paramextractor.].

The result of cloning is saved into DOMAIN.sm file which may be used with server.py to deploy created clone.
