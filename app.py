from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse
from ping3 import ping
import json 
import dns.resolver

app = Flask(__name__)

# Define your functions here

def get_page_load_time(url):
    try:
        start_time = time.time()
        response = requests.get(url)
        load_time = time.time() - start_time
        return load_time if response.status_code == 200 else None
    except requests.exceptions.RequestException:
        return None

def check_https(url):
    parsed_url = urlparse(url)
    return parsed_url.scheme == 'https'

def get_meta_data(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else ''
        description = soup.find('meta', attrs={'name': 'description'})
        description = description['content'] if description else ''
        return title, description
    except requests.exceptions.RequestException:
        return '', ''

def check_image_optimization(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        images = soup.find_all('img')
        optimized_images = sum(1 for img in images if img.has_attr('alt') and img['alt'])
        total_images = len(images)
        return optimized_images / total_images if total_images > 0 else 1
    except requests.exceptions.RequestException:
        return 0

def calculate_seo_score(url):
    weights = {
        'load_time': 20,
        'https': 20,
        'meta_tags': 20,
        'image_optimization': 20,
        'mobile_friendly': 20
    }
    load_time = get_page_load_time(url)
    load_time_score = max(0, (2 - load_time) / 2) if load_time else 0
    https_score = 1 if check_https(url) else 0
    title, description = get_meta_data(url)
    meta_tags_score = 1 if title and description else 0
    image_optimization_score = check_image_optimization(url)
    mobile_friendly_score = 0.9  # Replace with actual score from PageSpeed Insights API
    total_score = (
        load_time_score * weights['load_time'] +
        https_score * weights['https'] +
        meta_tags_score * weights['meta_tags'] +
        image_optimization_score * weights['image_optimization'] +
        mobile_friendly_score * weights['mobile_friendly']
    )
    max_score = sum(weights.values())
    seo_score = (total_score / max_score) * 100
    return seo_score

def get_ping(url):
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    if not hostname:
        return None
    response_time = ping(hostname)
    return response_time * 1000 if response_time is not None else None

def get_dns_response_time(url):
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    if not hostname:
        return None
    try:
        start_time = time.time()
        dns.resolver.resolve(hostname, 'A')
        dns_response_time = time.time() - start_time
        return dns_response_time
    except:
        return None

def get_ttfb(url):
    session = requests.Session()
    request = requests.Request("GET", url)
    prepared_request = session.prepare_request(request)
    start = time.time()
    response = session.send(prepared_request, stream=True)
    ttfb = time.time() - start
    return ttfb if response.status_code == 200 else None

def get_website_data(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else 'Title not found'
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc['content'] if meta_desc else 'Meta description not found'
        return {
            'title': title,
            'meta_description': description,
        }
    except requests.exceptions.RequestException:
        return {}

def analyze_accessibility(url):
    response = requests.get(url)
    if response.status_code != 200:
        return None
    soup = BeautifulSoup(response.text, 'html.parser')
    alt_ok = sum(1 for img in soup.find_all('img') if img.has_attr('alt') and img['alt'])
    labels_ok = sum(1 for label in soup.find_all('label') if label.get('for'))
    total_inputs = len(soup.find_all(['input', 'select', 'textarea']))
    aria_count = len(soup.find_all(attrs={"aria-label": True}))
    accessibility_score = (
        (alt_ok / len(soup.find_all('img')) if len(soup.find_all('img')) > 0 else 1) * 25 +
        (labels_ok / total_inputs if total_inputs > 0 else 1) * 25 +
        (1 if len(soup.find_all("h1")) > 0 else 0) * 25 +
        (aria_count / 10 if aria_count > 0 else 0) * 25
    )
    return accessibility_score if accessibility_score <= 100 else 100

def analyze_with_pagespeed(url):
    api_key = 'AIzaSyC1XRxVYhW0SFh3z00ZPx9eawptNsg5gAQ'
    endpoint = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&key={api_key}"
    
    try:
        response = requests.get(endpoint)
        if response.status_code == 200:
            data = response.json()
            if "lighthouseResult" in data:
                insights = {
                    "Performance Score": data["lighthouseResult"]["categories"]["performance"]["score"] * 100,
                    "First Contentful Paint": data["lighthouseResult"]["audits"]["first-contentful-paint"]["displayValue"],
                    "Largest Contentful Paint": data["lighthouseResult"]["audits"]["largest-contentful-paint"]["displayValue"],
                    "Cumulative Layout Shift": data["lighthouseResult"]["audits"]["cumulative-layout-shift"]["displayValue"],
                }
                return insights
            else:
                print("Error: 'lighthouseResult' not found in the response data.")
                return None
        else:
            print(f"Error: API returned status code {response.status_code}")
            print("Response:", response.json())  # Print the error details
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None


# Flask routes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    url = request.json.get('url')
    results = {}
    results['seo_score'] = calculate_seo_score(url)
    results['ping'] = get_ping(url)
    results['dns_response_time'] = get_dns_response_time(url)
    results['https_enabled'] = check_https(url)
    results['ttfb'] = get_ttfb(url)
    results['accessibility_score'] = analyze_accessibility(url)
    results['pagespeed_insights'] = analyze_with_pagespeed(url)  # Integrate PageSpeed insights
    website_data = get_website_data(url)
    results.update(website_data)
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
