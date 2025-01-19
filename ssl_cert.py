import ssl
import certifi
import urllib.request

url = "https://google.com"

# Create an SSL context using certifi's certificate store
ssl_context = ssl.create_default_context(cafile=certifi.where())

# Make the request
response = urllib.request.urlopen(url, context=ssl_context)
print(response.read())