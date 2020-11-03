#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This class defines how the willhaben website will be crawled
"""

# default python packages
import datetime
import re
import logging
# installed packages
import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from bs4 import BeautifulSoup
# project modules
from webscraper_for_sophie.items import CondoItem


class WillhabenSpider(scrapy.Spider):
    """
    Spider‘s are classes which define how a certain site (or a group of sites)
    will be scraped, including how to perform the crawl (i.e. follow links) and
    how to extract structured data from their pages (i.e. scraping items)
    Here is a summary of the most important spider attributes. A detailed
    documentation can be found in the `official Scrapy documentation
    """
    START_URL = 'https://www.willhaben.at/iad/immobilien/eigentumswohnung/steiermark/graz/'
    ITEM_URL_REGEX = r"\"url\":\"(\/iad\/immobilien\/d\/eigentumswohnung\/steiermark\/graz\/[a-z,A-Z,0-9,-]+\/)\""
    ITEM_IMG_REGEX = r'"referenceImageUrl":"(https:\/\/cache.willhaben.at[-a-zA-Z0-9@:%._\+~#=/]+)"'
    BASE_URL = "https://willhaben.at"
    name = 'willhaben'
    allowed_domains = ['willhaben.at']
    start_urls = [
        START_URL
    ]

    def parse(self, response):
        """
        This is the default callback used by Scrapy to process downloaded
        responses, when their requests don’t specify a callback like the
        `start_urls`
        """

        # get item urls and yield a request for each item
        relative_item_urls = re.findall(self.ITEM_URL_REGEX, response.text)
        item_count = len(relative_item_urls)
        if item_count == 25:
            logging.info("Found {} items on page {}".format(
                item_count, response.url))
        elif item_count >= 20:
            logging.warning("Found only {} items on page {}".format(
                item_count, response.url))
        else:
            logging.error("Found only {} items on page {}".format(
                item_count, response.url))

        # for relative_item_url in relative_item_urls:
        #     full_item_url = self.BASE_URL + relative_item_url
        #     # print(full_item_url)
        #     yield scrapy.Request(full_item_url, self.parse_item)
        full_item_url = self.BASE_URL + relative_item_urls[0]
        yield scrapy.Request(full_item_url, self.parse_item)

        # get the next page of the list
        soup = BeautifulSoup(response.text, 'lxml')
        pagination_btn = soup.find(
            'a', attrs={"data-testid": "pagination-top-next-button"})
        next_page_url = self.BASE_URL + pagination_btn['href']
        # yield scrapy.Request(next_page_url, self.parse)
        # TODO error handling

    def parse_item(self, response):
        """returns/yields a :py:class:`WillhabenItem`.

        This is the callback used by Scrapy to parse downloaded item pages.
        """
        item = CondoItem()
        item.set_default_values()
        item['url'] = response.url
        item['discovery_date'] = datetime.datetime.now().strftime("%Y-%m-%d")
        # time could also be added if needed: "%Y-%m-%d %H:%M:%S"

        soup = BeautifulSoup(response.text, 'lxml')
        # remove all script tags from soup
        for s in soup('script'):
            s.clear()

        # title
        title_tag = soup.find('h1')
        if title_tag:
            item['title'] = title_tag.get_text()
        else:
            logging.error("title element not found on page " + item['url'])

        # price
        price_tag = soup.find(
            'span', attrs={"data-testid": "contact-box-price-box-price-value"})
        if price_tag:
            price_text = price_tag.get_text()
            cleaned_price_text = price_text.replace('.', '')
            match = re.search(r'\d+', cleaned_price_text)
            if match:
                item['price'] = match[0]  # The entire match
            else:
                logging.error("price parsing failed on page " + item['url'])
        else:
            logging.error("price element not found on page " + item['url'])

        # size
        size_tag = soup.find(
            'div', attrs={"data-testid": "ad-detail-teaser-attribute-0"})
        if size_tag:
            size_text = size_tag.get_text()
            match = re.search(r'\d+', size_text)
            if match:
                item['size'] = match[0]  # The entire match
            else:
                logging.error("size parsing failed on page " + item['url'])
        else:
            logging.error("size element not found on page " + item['url'])

        # address, postal_code and district
        location_address_tag = soup.find(
            'div', attrs={"data-testid": "object-location-address"})
        if location_address_tag:
            location_address_text = location_address_tag.get_text()
            # parse address
            item['address'] = location_address_text
            # parse postal_code
            match = re.search(r'8\d\d\d', location_address_text)
            if match:
                item['postal_code'] = match[0]  # The entire match
            else:
                logging.error(
                    "postal_code parsing failed on page " + item['url'])
            # parse district
            match = re.search(r'8\d\d\d ([^,]+)', location_address_text)
            if match:
                item['district'] = match[1]  # The first group
            else:
                logging.error(
                    "district parsing failed on page " + item['url'])
        else:
            logging.error("element for address, postal_code and district " +
                          "not found on page " + item['url'])

        # willhaben_code
        willhaben_code_tag = soup.find(
            'span', attrs={"data-testid": "ad-detail-ad-id"})
        if willhaben_code_tag:
            willhaben_code_text = willhaben_code_tag.get_text()
            match = re.search(r'\d+', willhaben_code_text)
            if match:
                item['willhaben_code'] = match[0]  # The first group
            else:
                logging.error(
                    "willhaben_code parsing failed on page " + item['url'])
        else:
            logging.error(
                "willhaben_code element not found on page " + item['url'])

        # edit_date
        edit_date_tag = soup.find(
            'span', attrs={"data-testid": "ad-detail-ad-edit-date"})
        if edit_date_tag:
            item['edit_date'] = edit_date_tag.get_text()
        else:
            logging.error("edit_date element not found on page " + item['url'])

        # commission_fee
        body_tag = soup.find('article')
        if body_tag:
            body_text = body_tag.get_text()
            if 'provisionsfrei' in body_text.lower():
                item['commission_fee'] = 0
            else:
                item['commission_fee'] = 3.6
        else:
            logging.error(
                "commission_fee element not found on page " + item['url'])

        # # ad_info_desc     and     ad_info_values
        # attr_groups = soup.findAll(
        #     'div', attrs={"data-testid": "attribute-group"})
        # ad_info_descriptions = []
        # ad_info_values = []
        # for attr_group in attr_groups:
        #     attributes = attr_group.findAll(
        #         'li', attrs={"data-testid": "attribute"})
        #     for attr in attributes:
        #         ad_info_desc = attr.find(
        #             'div', attrs={"data-testid": "attribute-name"})
        #         ad_info_value = attr.find(
        #             'div', attrs={"data-testid": "attribute-value"})
        #         if ad_info_desc:
        #             ad_info_descriptions.append(ad_info_desc.get_text())
        #             if ad_info_value:
        #                 ad_info_values.append(
        #                     ad_info_value.get_text().strip())
        #             else:
        #                 ad_info_values.append('')

        # item['ad_info_desc'] = ad_info_descriptions
        # item['ad_info_values'] = ad_info_values

        # futher item processing is done in the item pipeline
        yield item
