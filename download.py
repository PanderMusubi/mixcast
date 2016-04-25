#!/usr/bin/env python3

# name: update.py
# description: TODO
# license: MIT
# date: 2016-04-16
# see also:
# * http://www.feedforall.com/itune-tutorial-tags.htm
# * http://www.rssboard.org/rss-profile
# * http://mixcloud-rss.georgipavlov.com
# * http://bits.meloncholy.com/mixcloud-rss (not used anymore)
# required elements: description, link, name, title

from datetime import datetime
from urllib import request
from soundscrape import soundscrape
from glob import glob
from os import path, rename, remove
from sys import argv
import xml.etree.ElementTree as ET


def encode(string):
    """Escapes a string for usage in XML
    
    :param string: string to encode
    :type: str
    :returns: encoded string
    :rtype: str
    """

    if '&#39;' in string or '&quot;' in string or '&lt;' in string or '&gt;' in string or '&amp;' in string:  # already encoded
        return string

    magic = 'ßﬁæœXXXa_a_a666mixcast'
    if magic in string:
        print('ERROR: string encoding failed')
        exit(1)
    ampersand = False
    if '&' in string:
        ampersand = True
    string = string.replace('&', magic)
    string = string.replace("'", '&#39;')
    string = string.replace('"', '&quot;')
    string = string.replace('<', '&lt;')
    string = string.replace('>', '&gt;')
    string = string.replace(magic, '&amp;')
    if ampersand and '&amp;' not in string:
        print('ERROR: string encoding failed')
        exit(1)
    return string


def decode(string):
    """Unescape string originating from XML
    
    :param string: string to decode
    :type: str
    :returns: decoded string
    :rtype: str
    """

    if '&#39;' not in string and '&quot;' not in string and '&lt;' not in string and '&gt;' not in string and '&amp;' not in string:  # already decoded
        return string

    string = string.replace('&#39;', "'")
    string = string.replace('&quot;', '"')
    string = string.replace('&lt;', '<')
    string = string.replace('&gt;', '>')
    string = string.replace('&amp;', '&')
    return string


def get_rss(mixcloud_account):
    """Downloads RSS feed with latest uploads to Mixcloud
    
    :param mixcloud_account: account name for Mixcloud
    :type: str
    :returns: decoded string
    :rtype: str
    """

    url = 'http://mixcloud-rss.georgipavlov.com/{}/m4a/30'.format(
        mixcloud_account)
    hdr = {'User-Agent': 'Mozilla/5.0'}
    req = request.Request(url, headers=hdr)
    try:
        return request.urlopen(req).read().decode('utf-8')
    except:
        print('ERROR: Could not retrieve url {}'.format(url))
        exit(1)


def scan_files():
    """Scans directory for M4A files which have been downloaded from Mixcloud
    
    :returns: decoded string
    :rtype: dictionary with M4A filenames as keys
    """

    # scan which files have been downladed
    files = {}
    for filename in glob('*.m4a'):
        files[filename] = 1
    return files


def download_or_delete(items, files, debug=False):
    """Download new M4A files from Mixcloud and deletes old M4A files
    
    :param items: TODO
    :type: dictionary
    :param files: TODO
    :type: dictionary
    :param debug: TODO
    :type: boolean
    """

    # download files in items
    for filename, values in sorted(items.items()):
        if filename not in files:
            source = values['source']
            if debug:
                if not path.isfile(source):
                    tmp = file(source, 'w')
                    tmp.write('debug\n')
            else:
                soundscrape.scrape_mixcloud_url(values['link'])
                if source != filename:
                    rename(source, filename)
    # remove files that not in items
    for key, values in sorted(files.items()):
        if key not in items:
            remove(key)


def write_items(items, filenames, urlbase, rssfile, debug=False):
    """Writes all items to RSS file
    
    :param items: TODO
    :type: dictionary
    :param filenames: TODO
    :type: list
    :param rssfile: TODO
    :type: file in write mode
    """

    for filename in filenames:  # for correct sorting
        values = items[filename]
        rssfile.write('\n')
        rssfile.write('        <item>\n')
        url = 'http://{}/{}'.format(urlbase, encode(values['source']))
        rssfile.write('            <title>{}</title>\n'.format(values['title']))
        rssfile.write('            <link>{}</link>\n'.format(url))
        rssfile.write('            <description><![CDATA[{}]]></description>\n'.format(values['description']))
        rssfile.write('            <pubDate>{}</pubDate>\n'.format(values['pubDate']))
        rssfile.write('            <enclosure url="{}" length="{}" type="audio/x-m4a"/>\n'.format(url, path.getsize(filename)))
        if values['itunesAuthor']:
            rssfile.write('            <itunes:author>{}<itunes:author/>\n'.format(values['itunesAuthor']))
        if values['itunesSubtitle']:
            rssfile.write('            <itunes:subtitle>{}<itunes:subtitle/>\n'.format(values['itunesSubtitle']))
        else:
            if debug:
                rssfile.write('            <itunes:subtitle></itunes:subtitle>\n')
        if values['itunesSummary']:
            rssfile.write('            <itunes:summary><![CDATA[{}]]><itunes:summary/>\n'.format(values['itunesSummary']))
        if values['itunesDuration']:
            rssfile.write('            <itunes:duration>{}<itunes:duration/>\n'.format(values['itunesDuration']))
        rssfile.write('            <guid>{}</guid>\n'.format(url))
        if values['itunesImage']:
            rssfile.write('            <itunes:image href="{}" />\n'.format(values['itunesImage']))
# TODO        rssfile.write('        <itunes:keywords></itunes:keywords>\n')
        rssfile.write('        </item>\n')


def main():
    """Main program
    """
    
    if len(argv) != 5:
        print('ERROR: missing account name (e.g. ifmx), hostname (e.g. intergalacticfm.com), podcast path (e.g. podcast/ or \'\') and email prefix (e.g. info)')
        exit(1)

    # settings
    debug = False  # when True doens fake download and creates rss.xml to copy for podcast-rss-output-example-ifmx.xml
    mixcloud_account = argv[1]
    hostname = argv[2]
    website = 'http://{}'.format(hostname)
    urlbase = '{}/{}'.format(hostname, argv[3])
    email = '{}@{}'.format(argv[4], hostname)

    files = scan_files()

    data = get_rss(mixcloud_account)
    # scan rss feed with uploads for metadata
    rssTitle = None
    rssDescription = None
    rssPubDate = None
    rssLanguage = None
    rssItunesAuthor = None
    rssItunesSubtitle = None
    rssItunesSummary = None
    rssImageUrl = None
    rssImageTitle = None  # alles nalopen of leeg gevuld kan worden met zinvols
    rssImageWidth = None
    rssImageHeight = None
    items = {}
    filenames = []  # for correct sorting
    rss = ET.fromstring(data)
    for channel in rss:
        for item in channel:
            if item.tag == 'title':
                rssTitle = encode(item.text)
            elif item.tag == '{http://www.w3.org/2005/Atom}link':
                continue  # will be custom from argv
            elif item.tag == 'link':
                continue  # will be custom from argv
            elif item.tag == 'description':
                rssDescription = item.text  # comes from and goes into CDATA
            elif item.tag == 'pubDate':
                rssPubDate = item.text
                if rssPubDate == '':
                    rssPubDate = None
            elif item.tag == 'language':
                rssLanguage = item.text
                if rssLanguage == '':
                    rssLanguage = None
            elif item.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}author':
                rssItunesAuthor = item.text
                if rssItunesAuthor == '':
                    rssItunesAuthor = None
            elif item.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}subtitle':
                rssItunesSubtitle = item.text
                if rssItunesSubtitle == '':
                    rssItunesSubtitle = None
            elif item.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}summary':
                rssItunesSummary = item.text  # comes from and goes into CDATA
                if rssItunesSummary == '':
                    rssItunesSummary = None
            elif item.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}owner':
                continue  # name derived from rss title and email from argv
            elif item.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}image':
                rssImageUrl = item.attrib['href']
                if rssImageUrl == '':
                    rssImageUrl = None
            elif item.tag == 'image':
                for element in item:
                    if element.tag == 'url':
                        image = element.text
                        if image == '':
                            image = None
                        if not rssImageUrl and image:
                            rssImageUrl = image
                    elif element.tag == 'title':
                        rssImageTitle = element.text
                        if rssImageTitle == '':
                            rssImageTitle = None
                    elif element.tag == 'link':
                        continue  # name derived from argv
                    elif element.tag == 'width':
                        rssImageWidth = element.text
                        if rssImageWidth == '':
                            rssImageWidth = None
                    elif element.tag == 'height':
                        rssImageHeight = element.text
                        if rssImageHeight == '':
                            rssImageHeight = None
            elif item.tag == 'item':
                title = None
                link = None
                description = None
                pubDate = None
                itunesAuthor = None
                itunesSubtitle = None
                itunesSummary = None
                itunesDuration = None
                itunesImage = None
                filename = None
                source = None
                for field in item:
                    if field.tag == 'title':
                        title = encode(field.text)  # half encoded
                        source = '{} - {}.m4a'.format(rssTitle, title)
                        source = source.replace(':', '-')
                        source = source.replace('/', '-')
                        filename = decode(source)
                    elif field.tag == 'link':
                        link = field.text  # will be only used for download
                    elif field.tag == 'description':
                        description = field.text  # comes from and goes to CDATA
                    elif field.tag == 'pubDate':
                        pubDate = field.text
                    elif field.tag == 'enclosure':
                        continue  # will be custom from argv
                    elif field.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}author':
                        itunesAuthor = field.text
                    elif field.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}subtitle':
                        itunesSubtitle = field.text
                    elif field.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}summary':  # comes from and goes to CDATA
                        itunesSummary = field.text
                    elif field.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}duration':
                        itunesDuration = field.text
                    elif field.tag == 'guid':
                        continue  # will be custom from argv
                    elif field.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}image':
                        itunesImage = field.attrib['href']
                items[filename] = {'title': title, 'source': source, 'link': link, 'description': description, 'pubDate': pubDate, 'itunesAuthor': itunesAuthor, 'itunesSubtitle': itunesSubtitle, 'itunesSummary': itunesSummary, 'itunesDuration': itunesDuration, 'itunesImage': itunesImage}
                filenames.append(filename)  # for correct sorting

    # download newly available uploads according to rss feed
    download_or_delete(items, files, debug)

    # write rss file
    rssfile = open('rss.xml', 'w')
    rssfile.write('<?xml version="1.0"?>\n')
    rssfile.write('<rss xmlns:atom="http://www.w3.org/2005/Atom"  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">\n')
    rssfile.write('    <channel>\n')

    rssfile.write('        <title>{}</title>\n'.format(rssTitle))
    rssfile.write('        <atom:link href="http://{}/rss.xml" rel="self" type="application/rss+xml"/>\n'.format(urlbase))
    rssfile.write('        <link>http://{}</link>\n'.format(hostname))
    rssfile.write('        <description><![CDATA[{}]]></description>\n'.format(rssDescription))
    rssfile.write('        <lastBuildDate>{}</lastBuildDate>\n'.format(
        datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')))
    if rssPubDate:
        rssfile.write('        <pubDate>{}</pubDate>\n'.format(rssPubDate))
    rssfile.write('        <generator>http://github.com/intergalacticfm/mixcast</generator>\n')
    if rssLanguage:
        rssfile.write('        <language>{}</language>\n'.format(rssLanguage))
    if rssItunesAuthor:
        rssfile.write('        <itunes:author>{}</itunes:author>\n'.format(rssItunesAuthor))
    if rssItunesSubtitle:
        rssfile.write('        <itunes:subtitle>{}</itunes:subtitle>\n'.format(rssItunesSubtitle))
    else:
        if debug:
            rssfile.write('        <itunes:subtitle></itunes:subtitle>\n')
    if rssItunesSummary:
        rssfile.write('        <itunes:summary><![CDATA[{}]]></itunes:summary>\n'.format(rssItunesSummary))
    rssfile.write('        <itunes:owner>\n')
    rssfile.write('            <itunes:name>{}</itunes:name>\n'.format(rssTitle))
    rssfile.write('            <itunes:email>{}</itunes:email>\n'.format(email))
    rssfile.write('        </itunes:owner>\n')
    rssfile.write('        <webMaster>{}</webMaster>\n'.format(email))
    rssfile.write('        <managingEditor>{}</managingEditor>\n'.format(email))
    rssfile.write('        <copyright>{}</copyright>\n'.format(rssTitle))
    rssfile.write('        <itunes:category text="Music" />\n')
    if rssImageUrl:
        rssfile.write('        <itunes:image>{}</itunes:image>\n'.format(rssImageUrl))
        rssfile.write('        <image/>\n')
        rssfile.write('            <url>{}</url>\n'.format(rssImageUrl))
        if rssImageTitle:
            rssfile.write('            <title>{}</title>\n'.format(rssImageTitle))
        else:
            rssfile.write('            <title>{}</title>\n'.format(rssTitle))
        rssfile.write('            <link>http://{}</link>\n'.format(hostname))
        if rssImageWidth:
            rssfile.write('            <width>{}</width>\n'.format(rssImageWidth))
        if rssImageHeight:
            rssfile.write('            <height>{}</height>\n'.format(rssImageHeight))
        rssfile.write('        <image/>\n')

    write_items(items, filenames, urlbase, rssfile, debug)

    rssfile.write('    </channel>\n')
    rssfile.write('</rss>\n')


if __name__ == "__main__":
    main()
