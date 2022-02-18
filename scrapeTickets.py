import requests
from bs4 import BeautifulSoup
import time
import smtplib, ssl
import pygame as pg
import os

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import webbrowser

# .env file e-mail variables:
# EMAIL_HOST
# EMAIL_PORT
# EMAIL_HOST_USER
# EMAIL_HOST_PASSWORD
from dotenv import load_dotenv

load_dotenv()

# url to ticketswap page and to who it sends an email if ticket is found
# ex; Lowlands: https://www.ticketswap.nl/event/lowlands-festival-2022/weekend-tickets/dad6ecb1-d6da-4586-b78c-508a70abf42a/1970961
url = input("Please enter the specific ticket link from ticketswap.nl: ")

# MacOS
# chrome_path = 'open -a /Applications/Google\ Chrome.app %s'

# Windows
chrome_path = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s'

# Linux
# chrome_path = '/usr/bin/google-chrome %s'


# user input for settings
receiver_email = input("Enter your email to notify when ticket is found: ")
beepy = input("Want your PC to beep when ticket is found? (Sound needs to be on) (Y/N): ")
testing_email_input = input("Wanna send a test email beforehand? (Y/N): ")

if testing_email_input == "Y":
    testing_email = True
elif testing_email_input == "N":
    testing_email = False
else:
    testing_email = False

if beepy == "Y":
    go_beep = True
elif beepy == "N":
    go_beep = False
else:
    go_beep = False

# how many ms between total ticket requests
frequency = 500

##################################################################### Beepy noise when ticket is found
def play_sound(sound_file):
    """
    will load the whole sound into memory before playback
    """
    sound = pg.mixer.Sound(sound_file)
    clock = pg.time.Clock()
    sound.play()
    # how often to check active playback
    frame_rate = 30
    while pg.mixer.get_busy():
        clock.tick(frame_rate)


FREQ = 18000   # play with this for best sound
BITSIZE = -16  # here unsigned 16 bit
CHANNELS = 2   # 1 is mono, 2 is stereo
BUFFER = 1024  # audio buffer size, number of samples

pg.mixer.init(FREQ, BITSIZE, CHANNELS, BUFFER)

# pick a wave (.wav) sound file you have
go_beep = "beep.wav"

#################################################################### email email_server.server if ticket found
smtp_server = os.getenv("EMAIL_HOST")
port = os.getenv("EMAIL_PORT")
sender_email = os.getenv("EMAIL_HOST_USER")
password = os.getenv("EMAIL_HOST_PASSWORD")

# creating the email when ticket is found
ticketfound_message = f"""\
<html>
    <body>
        <p>Ticket is found. Go to this link</p>
        <a href="{url}" target="_blank">{url}</a>
    </body>
</html>
"""
# setting subject, sender email and receiver email
message = MIMEMultipart("alternative")
message["Subject"] = "scrapeTickets: TICKET FOUND"
message["From"] = sender_email
message["To"] = receiver_email

# mime up and attach email to message
mimed_email_msg = MIMEText(ticketfound_message, "html")
message.attach(mimed_email_msg)

# GET request headers for scraping the ticketswap page
headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '3600',
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
    }

# Create a secure SSL context for email
context = ssl.create_default_context()

# testing the beepy
if beepy:
    print("Testing the beepy noise...")
    play_sound(go_beep)
    print("beeped.")

######################################################################## start the email server

print("Creating email server...")
with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
    print("Logging in to server...")
    server.login(sender_email, password)
    print("Logged in successfully")
    if testing_email:
        print("Setting up test email...")
        test_message = MIMEMultipart("alternative")
        test_message["Subject"] = "TestMessage if ticket is found."
        test_message["From"] = sender_email
        test_message["To"] = receiver_email
        test_message.attach(mimed_email_msg)
        print("Set up test email successfully")
        print(f"Sending test email to {receiver_email}...")
        server.sendmail(sender_email, receiver_email, test_message)
        print("Test email sent successfully")

    n = 1
    totaltime_ms = 0
    print("Scraping tickets...")
    
    # Keep finding tickets indefinitely
    while True:
        starttime = time.perf_counter()
        # get the ticket page
        req = requests.get(url, headers)
        request_time = time.perf_counter() - starttime
        # parse the html soup
        soup = BeautifulSoup(req.content, 'html.parser')

        # The available ticket number is within a div with class "css-5j1f2g" like this:
        #
        # <div class="css-5j1f2g ...">
        #   <div first-child ...>
        #       <span ...>
        #           0
        #       </span>
        #   </div>
        # </div>
        #
        # The following forloops finds this exactly and breaks the loops when found.
        for div in soup.find_all(class_='css-5j1f2g'):
            # breaks after first <div> element found
            for childdiv in div.find_all('div'):
                # specific ticket amount number from <span></span>
                ticketcount = int(childdiv.span.string)
                
                # FOUND A TICKET
                if ticketcount > 0:
                    print(f"{ticketcount} TICKET(S) FOUND! Link: {url}")

                    # open the browser to the ticket page
                    print("Opening webpage...")
                    webbrowser.get(chrome_path).open(url)

                    # wake the fuck up bitch
                    if beepy:
                        play_sound(go_beep)
                    
                    # store it if you didnt wake up so you can feel bad about it
                    with open("Ticketsfound.txt", "w") as f:
                        f.write(f"{datetime.datetime.now()}, {ticketcount} ticket(s)")

                    # send the email to notify the user
                    print(f"Sending E-mail to {receiver_email}...")
                    server.sendmail(sender_email, receiver_email, message)
                    print("Sent email succesfully. Moving on!")
                break
            break
            
        # stdout info
        extract_ticketcount_time = time.perf_counter() - request_time - starttime
        totaltime_attempt = float(1000 * (extract_ticketcount_time + request_time))
        totaltime_ms += totaltime_attempt
        print(f"{ticketcount} tickets available. Time (GET Request): {request_time}s. Time (Extracting from soup): {extract_ticketcount_time}s. Total time: {totaltime_ms / 1000}. Attempt {n}")

        
        n += 1
        
        # request can take longer than the given frequency time to request, dont sleep if so.
        sleep_time_ms = float(frequency - totaltime_attempt)
        if sleep_time_ms < 0:
            sleep_time_s = 0
        else:
            sleep_time_s = sleep_time_ms / 1000
            
            
        time.sleep(sleep_time_s)