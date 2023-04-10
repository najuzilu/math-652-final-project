import urllib3
import logging
import time


logger = logging.getLogger()


def lambda_handler(event, context):
    url = event.get("href")
    logging.info(f"Querying {url}")
    
    http = urllib3.PoolManager()
    try:
        r = http.request(
            "GET",
            url,
            retries=urllib3.Retry(3),
            headers=event.get("headers"),
        )
        time.sleep(10)
    except KeyError as e:
        logging.warning(f"Wrong format url {url}", e)
        return
    except urllib3.exceptions.MaxRetryError as e:
        logging.error(f"API unavailable at {url}", e)
        return
    return {
        "statusCode": 200,
        "body": r.data
    }
