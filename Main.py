from urllib import request
import requests
from bs4 import BeautifulSoup
import datetime
from telegram.ext import Updater, CommandHandler, InlineQueryHandler, MessageHandler, filters
from telegram import ReplyKeyboardMarkup

Months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
#NegativeWords = ["plunge", "meltdown", "tumble", "tumbling", "crash", "plummet", "sell-off", "slump", "panic", "sharp drop", "precipitous drop", "trims"]
#PositiveWords = ["rise", "climb", "rally", "soar", "soaring"]
#NeutralWords = ["etf", "stampede", "etfs"]
file = open("positive_words.txt")
PositiveWords = file.readline().split(",")
file = open("negative_words.txt")
NegativeWords = file.readline().split(",")
file = open("neutral_words.txt")
NeutralWords = file.readline().split(",")
Stories = []
Links = []
NewStories =[]
NewLinks = []
global EditingMode
EditingMode = False
global WordSelection
WordSelection = False
global Action
Action = ""
global WordsEdited
WordsEdited = ""

def GetStrippedHeadline(start,end, HTMLContent):
    Story = HTMLContent[start:end]
    Story = Story.replace("\\n", "").replace("\\t", "").replace("\\", "").replace(">", "").replace("&#x27;", "'").replace("xe2x80x99", "'")
    return Story

def ReutersArtcilePublishedToday(StartLocation, HTMLContent):
    DateStart = HTMLContent.find("<time class=\"article-time\">", StartLocation) + 30
    DateStart = HTMLContent.find(">", DateStart) + 1
    DateEnd = HTMLContent.find("</span>", DateStart)
    Date = str(HTMLContent[DateStart:DateEnd]).split(" ")
    CurrentDate = str(datetime.datetime.today().day)
    CurrentMonth = Months[datetime.datetime.today().month - 1][0:3]
    if str(CurrentDate) != Date[0] or CurrentMonth != Date[1]:
        return True
    else:
        return False

def ReutersDateAnalysis(Date):
    CurrentDate = str(datetime.datetime.today().day)
    CurrentMonth = Months[datetime.datetime.today().month - 1][0:3]
    if "am" in Date or "pm" in Date:
        return True
    else:
        Date = Date.split(" ")
        if str(CurrentDate) != Date[0] or CurrentMonth != Date[1]:
            return False
        else:
            return True

def FTIsArticlePublishedToday(StartLocation, HTMLContent):
    DateStart = HTMLContent.find("<div class=\"stream-card__date\">", StartLocation) + 32
    DateStart = HTMLContent.find(">", DateStart) + 1
    DateEnd = HTMLContent.find("</time>", DateStart)
    Date = HTMLContent[DateStart:DateEnd].split(" ")
    CurrentMonth = Months[datetime.datetime.today().month - 1]
    CurrentDate = datetime.datetime.today().day
    if str(CurrentDate) != Date[1] or CurrentMonth != Date[2].replace(",", ""):
        return True
    else:
        return False

def MarketwatchArticlePublishedToday(StartLocation, HTMLContent):
    DateStart = HTMLContent.find("<span class=\"article__timestamp\"", StartLocation)
    DateStart = HTMLContent.find(">", DateStart)
    DateEnd = HTMLContent.find("</span>", DateStart)
    Date = HTMLContent[DateStart:DateEnd].replace(",", "").replace(".", "").split(" ")
    CurrentDate = str(datetime.datetime.today().day)
    CurrentMonth = Months[datetime.datetime.today().month - 1][0:3]
    if str(CurrentDate) != Date[1] or CurrentMonth != Date[0]:
        return True
    else:
        return False

def CNBCArticlePublishedToday (StartLocation, HTMLContent):
    DateStart = HTMLContent.find("<span class=\"Card-time\">", StartLocation) + 24
    DateEnd = HTMLContent.find("</span>", DateStart)
    Date = HTMLContent[DateStart:DateEnd]
    if Date.find("hour") != -1 or Date.find("hours") != -1:
        return False
    else:
        Date = Date.replace(",", "").replace("th", "").split(" ")
        CurrentDate = str(datetime.datetime.today().day)
        CurrentMonth = Months[datetime.datetime.today().month - 1][0:3]
        if str(CurrentDate) != Date[2] or CurrentMonth != Date[1]:
            return True
        else:
            return False

def FetchArticles():
    print("Getting Reuters")

    resp = request.urlopen("https://uk.reuters.com/news/archive/fundsNews?date=today")
    HTMLContent = str(resp.read())
    StoryStart = HTMLContent.find("<div class=\"story-content\">") + 29
    DayEnded = ReutersArtcilePublishedToday(StoryStart, HTMLContent)
    while not DayEnded:
        LinkStart = HTMLContent.find("href=\"", StoryStart) + 6
        LinkEnd = HTMLContent.find("\">", LinkStart)
        Links.append("https://uk.reuters.com" + HTMLContent[LinkStart:LinkEnd])
        StoryStart = HTMLContent.find("<h3 class=\"story-title\">", StoryStart + 4) + 24
        StoryEnd = HTMLContent.find("</h3>", StoryStart)
        Stories.append(GetStrippedHeadline(StoryStart, StoryEnd, HTMLContent))
        StoryStart = HTMLContent.find("<div class=\"story-content\">", StoryEnd) + 29
        DayEnded = ReutersArtcilePublishedToday(StoryStart, HTMLContent)

    r1 = requests.get("https://uk.reuters.com/business/markets")
    page = r1.content
    soup = BeautifulSoup(page, 'html5lib')
    Headlines = soup.find_all('div', class_='story-content')
    ReuterLinks = []
    for Headline in Headlines:
        if "article" in Headline.find('a')['href'] and Headline.find('a')['href'] not in ReuterLinks:
            if Headline.find('time') != None:
                Today = ReutersDateAnalysis(Headline.find('time').get_text().strip())
            else:
                Today = True
            if Today:
                Stories.append(Headline.find('a').get_text().strip())
                Links.append("https://uk.reuters.com/" + Headline.find('a')['href'])
                ReuterLinks.append(Headline.find('a')['href'])

    ############################################################################ Bloomberg(Doesn't work)

    resp = request.urlopen("https://www.bloomberg.com/markets/etfs")
    HTMLContent = str(resp.read())
    StoryStart = HTMLContent.find("<div class=\"hero-module__info \">") + 34
    while StoryStart != 33:
        StoryStart = HTMLContent.find(">", StoryStart) + 1
        StoryEnd = HTMLContent.find("</a>", StoryStart)
        Stories.append(GetStrippedHeadline(StoryStart,StoryEnd))
        StoryStart = HTMLContent.find("<div class=\"hero-module__info \">", StoryEnd + 4) + 34

    ########################################################################### Financial Times

    print("Getting FT")

    resp = request.urlopen("https://www.ft.com/equities")
    HTMLContent = str(resp.read())
    StoryStart = HTMLContent.find("<li class=\"o-teaser-collection__item o-grid-row \">") + 52
    DayEnded = FTIsArticlePublishedToday(StoryStart, HTMLContent)
    while not DayEnded:
        LinkStart = HTMLContent.find("href=\"", StoryStart) + 6
        LinkEnd = HTMLContent.find("\"", LinkStart)
        Links.append("https://www.ft.com" + HTMLContent[LinkStart:LinkEnd])
        StoryStart = HTMLContent.find("<div class=\"o-teaser__heading\">", StoryStart) + 34
        StoryStart = HTMLContent.find(">", StoryStart) + 1
        StoryEnd = HTMLContent.find("</a>", StoryStart)
        Stories.append(GetStrippedHeadline(StoryStart,StoryEnd, HTMLContent))
        StoryStart = HTMLContent.find("<a", StoryEnd)
        StoryStart = HTMLContent.find(">", StoryStart)
        StoryEnd = HTMLContent.find("</a>", StoryStart)
        Stories[len(Stories)-1] = Stories[len(Stories)-1] + " / " + GetStrippedHeadline(StoryStart, StoryEnd, HTMLContent)
        StoryStart = HTMLContent.find("<li class=\"o-teaser-collection__item o-grid-row \">", StoryEnd) + 52
        DayEnded = FTIsArticlePublishedToday(StoryStart, HTMLContent)

    resp = request.urlopen("https://www.ft.com/markets")
    HTMLContent = str(resp.read())
    StoryStart = HTMLContent.find("<li class=\"o-teaser-collection__item o-grid-row \">") + 52
    DayEnded = FTIsArticlePublishedToday(StoryStart, HTMLContent)
    while not DayEnded:
        LinkStart = HTMLContent.find("href=\"", StoryStart) + 6
        LinkEnd = HTMLContent.find("\"", LinkStart)
        Links.append("https://www.ft.com" + HTMLContent[LinkStart:LinkEnd])
        StoryStart = HTMLContent.find("<div class=\"o-teaser__heading\">", StoryStart) + 34
        StoryStart = HTMLContent.find(">", StoryStart) + 1
        StoryEnd = HTMLContent.find("</a>", StoryStart)
        Stories.append(GetStrippedHeadline(StoryStart, StoryEnd, HTMLContent))
        StoryStart = HTMLContent.find("<a", StoryEnd)
        StoryStart = HTMLContent.find(">", StoryStart)
        StoryEnd = HTMLContent.find("</a>", StoryStart)
        Stories[len(Stories) - 1] = Stories[len(Stories) - 1] + " / " + GetStrippedHeadline(StoryStart, StoryEnd, HTMLContent)
        StoryStart = HTMLContent.find("<li class=\"o-teaser-collection__item o-grid-row \">", StoryEnd) + 52
        DayEnded = FTIsArticlePublishedToday(StoryStart, HTMLContent)

    ##############################################################Marketwatch

    print("Getting Marketwatch")

    try:
        resp = request.urlopen("https://www.marketwatch.com/investing/etf")
        HTMLContent = str(resp.read())
        StoryStart = HTMLContent.find("<h3 class=\"article__headline\">")
        DayEnded = MarketwatchArticlePublishedToday(StoryStart, HTMLContent)
        while not DayEnded:
            LinkStart = HTMLContent.find("href=\"", StoryStart) + 6
            LinkEnd = HTMLContent.find("\"", LinkStart)
            Links.append(HTMLContent[LinkStart:LinkEnd])
            print()
            StoryStart = HTMLContent.find("<p class=\"article__summary\">", StoryStart) + 30
            StoryEnd = HTMLContent.find("</p>", StoryStart)
            Stories.append(GetStrippedHeadline(StoryStart, StoryEnd, HTMLContent))
            StoryStart = HTMLContent.find("<h3 class=\"article__headline\">", StoryEnd)
            DayEnded = MarketwatchArticlePublishedToday(StoryStart, HTMLContent)
    except Exception as ex:
        print(ex)

    ############################################################CNBC

    print("Getting CNBC")
    resp = request.urlopen("https://www.cnbc.com/investing/")
    HTMLContent = str(resp.read())
    StoryStart = HTMLContent.find("<div class=\"Card-titleAndFooter\">") + 35
    DayEnded = CNBCArticlePublishedToday(StoryStart, HTMLContent)
    while not DayEnded:
        LinkStart = HTMLContent.find("href=\"h", StoryStart) + 6
        LinkEnd = HTMLContent.find("\"", LinkStart)
        Links.append(HTMLContent[LinkStart:LinkEnd])
        StoryStart = HTMLContent.find("target=", StoryStart) + 9
        StoryStart = HTMLContent.find("<div>", StoryStart) + 5
        StoryEnd = HTMLContent.find("</div>", StoryStart)
        Stories.append(GetStrippedHeadline(StoryStart, StoryEnd, HTMLContent))
        StoryStart = HTMLContent.find("<div class=\"Card-titleAndFooter\">", StoryEnd) + 35
        DayEnded = CNBCArticlePublishedToday(StoryStart, HTMLContent)

    print("Done")

def Sort(Stories, Links):
    NegativeStories = []
    PositiveStories = []
    NeutralStories = []
    NegativeLinks = []
    PositiveLinks = []
    NeutralLinks = []
    UnsortedStories = []
    UnsortedLinks = []
    for Story, Link in zip(Stories, Links):
        sorted = False
        for NegativeWord in NegativeWords:
            if Story.lower().find(NegativeWord) != -1:
                NegativeStories.append(Story)
                NegativeLinks.append(Link)
                sorted = True
                break
        if not sorted:
            for PositiveWord in PositiveWords:
                if Story.lower().find(PositiveWord) != -1:
                    PositiveStories.append(Story)
                    PositiveLinks.append(Link)
                    sorted = True
                    break
        if not sorted:
            for NeutralWord in NeutralWords:
                if Story.lower().find(NeutralWord) != -1:
                    NeutralStories.append(Story)
                    NeutralLinks.append(Link)
                    sorted = True
                    break
        if not sorted:
            UnsortedStories.append(Story)
            UnsortedLinks.append(Link)
    return [NegativeStories, PositiveStories, NeutralStories, NegativeLinks, PositiveLinks, NeutralLinks, UnsortedStories, UnsortedLinks]

def GetNewStories(OldStories):
    for Story, Link in zip(Stories,Links):
        if Story not in OldStories:
            NewStories.append(Story)
            NewLinks.append(Link)


def UpdateArticles():
    OldStories = Stories[:]
    Stories.clear()
    NewStories.clear()
    NewLinks.clear()
    FetchArticles()
    Sorted = Sort(Stories,Links)
    NegativeStories = Sorted[0]
    PositiveStories = Sorted[1]
    NeutralStories = Sorted[2]
    GetNewStories(OldStories)
    TextToSend = "Articles refreshed, total: " + str(len(Stories)) + ", \n" + str(len(NegativeStories) + len(PositiveStories) + len(NeutralStories)) + " are relevant \n" + str(len(NegativeStories)) + " indicating downward movement, \n" + str(len(PositiveStories)) + " indicating upward movement, \n" + str(len(NeutralStories)) + " don't indicate any movement \n" + "and " + str(len(NewStories)) + " are new"
    return TextToSend

def BotStart(bot, update):
    chat_id = update.message.chat_id
    bot.send_message(chat_id=chat_id,text="Welcome to the Article Seeker bot \nThe list of commands is as follows:\n\n''refresh'' - to update the headline list\n\n''new/all all/relevant/negative/positive/neutral'' to get new or all all/relevant/negative/positive/neutral articles\n\n''edit positive/negative/neutral words'' to edit the positive/negative or neutral keywords\n\n''search <word>'' to filter articles by a specific word, replacing <word> with the desired search term\n\n")

def GetArticlesText(Articles, Links):
    Text = ""
    if len(Articles) == 0:
        Text = "No artciles found in this category"
    else:
        for Article, Link in zip(Articles, Links):
            Text = Text + Article + "\nlink: " + Link + "\n\n"
    return Text

def WordOperation(Word, Operation, WordSet):
    if WordSet == "positive":
        if Operation == "add":
            if Word not in PositiveWords:
                PositiveWords.append(Word)
                ReturnText = Word + " successfully added to the positive keywords set"
            else:
                return Word + " is already a part of the positive keywords set"
        if Operation == "delete":
            if Word in PositiveWords:
                PositiveWords.remove(Word)
                ReturnText = Word + " successfully removed from the positive keywords set"
            else:
                return Word + " is not part of the positive keywords set"
        file = open("positive_words.txt", "w+")
        file.write(",".join(PositiveWords))
        ReturnText = ReturnText + " it now consists of the following:\n"
        for Word in PositiveWords:
            ReturnText = ReturnText + " -" + Word + "\n"
        return ReturnText

    if WordSet == "negative":
        if Operation == "add":
            if Word not in NegativeWords:
                NegativeWords.append(Word)
                ReturnText = Word + " successfully added to the negative keywords set"
            else:
                return Word + " is already a part of the negative keywords set"
        if Operation == "delete":

            if Word in NegativeWords:
                NegativeWords.remove(Word)
                ReturnText = Word + " successfully removed from the negative keywords set"
            else:
                return Word + " is not part of the negative keywords set"
        file = open("negative_words.txt", "w+")
        file.write(",".join(NegativeWords))
        ReturnText = ReturnText + " it now consists of the following:\n"
        for Word in NegativeWords:
            ReturnText = ReturnText + " -" + Word + "\n"
        return ReturnText

    if WordSet == "neutral":
        if Operation == "add":
            if Word not in NeutralWords:
                NeutralWords.append(Word)
                ReturnText = "''" + Word + "'' successfully added to the neutral keywords set"
            else:
                return Word + " is already a part of the neutral keywords set"
        if Operation == "delete":
            if Word in NeutralWords:
                NeutralWords.remove(Word)
                ReturnText = Word + " successfully removed from the neutral keywords set"
            else:
                return Word + " is not part of the neutral keywords set"
        file = open("neutral_words.txt", "w+")
        file.write(",".join(NeutralWords))
        ReturnText = ReturnText + " it now consists of the following:\n"
        for Word in NeutralWords:
            ReturnText = ReturnText + " -" + Word + "\n"
        return ReturnText

def CustomSearch(Word):
    MatchStories = []
    MatchLinks = []
    for Story, Link in zip(Stories, Links):
        if Word in Story.lower():
            MatchStories.append(Story)
            MatchLinks.append(Link)
    return [MatchStories, MatchLinks]

def MessageProcessing(bot, update):
    chat_id = update.message.chat_id
    message = str(update.message.text).lower()
    global EditingMode
    global WordSelection
    global WordsEdited
    global Action
    if EditingMode:
        if WordSelection:
            if message == "exit":
                WordSelection = False
                EditingMode = False
                TextToSend = "Editing finished"
            else:
                Result = WordOperation(message, Action, WordsEdited)
                bot.send_message(chat_id=chat_id,text=Result)
                TextToSend = "To " + Action + " another word just type it in, to exit type ''exit''"
        else:
            if message == "add":
                WordSelection = True
                Action = "add"
                TextToSend = "Now adding words to " + WordsEdited + " keywords\nSimply type the word you want to add\nOr type ''exit'' to stop editing"
            elif message == "delete":
                WordSelection = True
                Action = "delete"
                TextToSend = "Now deleting words from " + WordsEdited + " keywords\nSimply type the word you want to delete"
            elif message == "exit":
                EditingMode = False
                TextToSend = "Editing finished"
            else:
                TextToSend = "Unrecognised command ''" + message + "''\nTo add a word type ''add''\nTo delete a word type ''delete''\nTo exit editing type ''exit''"
    else:
        if message == "refresh":
            bot.send_message(chat_id=chat_id, text="Refreshing Articles, please wait...")
            TextToSend = UpdateArticles()
        elif message == "help":
            TextToSend = "The list of commands is as follows:\n\n''refresh'' - to update the headline list\n\n''new/all all/relevant/negative/positive/neutral'' to get new or all all/relevant/negative/positive/neutral articles\n\n''edit positive/negative/neutral words'' to edit the positive/negative or neutral keywords\n\n''search <word>'' to filter articles by a specific word, replacing <word> with the desired search term\n\n"
        else:
            message = message.split(" ")
            SimpleArticleListing = False
            if len(message) == 2:
                if message[0] == "all":
                    Sorted = Sort(Stories, Links)
                    NegativeStories = Sorted[0]
                    PositiveStories = Sorted[1]
                    NeutralStories = Sorted[2]
                    NegativeLinks = Sorted[3]
                    PositiveLinks = Sorted[4]
                    NeutralLinks = Sorted[5]
                    UnsortedStories = Sorted[6]
                    UnsortedLinks = Sorted[7]
                    SimpleArticleListing = True
                elif message[0] == "new":
                    Sorted = Sort(NewStories, NewLinks)
                    NegativeStories = Sorted[0]
                    PositiveStories = Sorted[1]
                    NeutralStories = Sorted[2]
                    NegativeLinks = Sorted[3]
                    PositiveLinks = Sorted[4]
                    NeutralLinks = Sorted[5]
                    UnsortedStories = Sorted[6]
                    UnsortedLinks = Sorted[7]
                    SimpleArticleListing = True
                if message[1]== "all" and SimpleArticleListing:
                    TextToSend = GetArticlesText(NegativeStories+PositiveStories+NeutralStories+UnsortedStories, NegativeLinks+PositiveLinks+NeutralLinks+UnsortedLinks)
                elif message[1] == "relevant" and SimpleArticleListing:
                    TextToSend = GetArticlesText(NegativeStories+PositiveStories+NeutralStories, NegativeLinks+PositiveLinks+NeutralLinks)
                elif message[1] == "negative" and SimpleArticleListing:
                    TextToSend = GetArticlesText(NegativeStories, NegativeLinks)
                elif message[1] == "positive" and SimpleArticleListing:
                    TextToSend = GetArticlesText(PositiveStories, PositiveLinks)
                elif message[1] == "neutral" and SimpleArticleListing:
                    TextToSend = GetArticlesText(NeutralStories, NeutralLinks)
                elif SimpleArticleListing:
                    TextToSend = "Unrecognised article type: " + str(message[1])
                if message[0] == "search":
                    Results = CustomSearch(message[1])
                    MatchStories = Results[0]
                    MatchLinks = Results[1]
                    TextToSend = GetArticlesText(MatchStories, MatchLinks)
                    TextToSend = "Articles containing ''" + message[1] + "'' in their title: \n" + TextToSend
                elif not SimpleArticleListing:
                    TextToSend = "Command ''" + " ".join(message) + "'' not recognise, for help type ''help''"
            elif len(message) == 3:
                if message[0] == "edit":
                    if message[1] == "positive":
                        EditingMode = True
                        WordsEdited = "positive"
                        TextToSend = "Now editing positive key words, they currently are: \n"
                        for Word in PositiveWords:
                            TextToSend = TextToSend + "-" + Word + "\n"
                        TextToSend = TextToSend + "\nIf you want to add a word type 'add'\nIf you want to delete a word type 'delete'\nIf you want to exit edit mode type 'exit'"
                    elif message[1] == "negative":
                        EditingMode = True
                        WordsEdited = "negative"
                        TextToSend = "Now editing negative key words, they currently are: \n"
                        for Word in NegativeWords:
                            TextToSend = TextToSend + "-" + Word + "\n"
                        TextToSend = TextToSend + "\nIf you want to add a word type 'add'\nIf you want to delete a word type 'delete'\nIf you want to exit edit mode type 'exit'"
                    elif message[1] == "neutral":
                        EditingMode = True
                        WordsEdited = "neutral"
                        TextToSend = "Now editing neutral key words, they currently are: \n"
                        for Word in NeutralWords:
                            TextToSend = TextToSend + "-" + Word + "\n"
                        TextToSend = TextToSend + "\nIf you want to add a word type 'add'\nIf you want to delete a word type 'delete'\nIf you want to exit edit mode type 'exit'"
                    else:
                        TextToSend = "Unrecognised word type: ''" + message[1] + "'' for help type ''help''"
                else:
                    TextToSend = "Command ''" + message + "'' unrecognized for help type ''help''"
            else:
                TextToSend = "Command unrecognized"
    if len(TextToSend) > 4000:
        OldLoc = 0
        while OldLoc + + 3000 < len(TextToSend):
            if TextToSend.find("\n", OldLoc + 3000) != -1:
                bot.send_message(chat_id=chat_id, text=TextToSend[OldLoc:TextToSend.find("\n", OldLoc + 3000)], disable_web_page_preview=True)
                OldLoc = TextToSend.find("\n", OldLoc + 3000)
            else:
                OldLoc = len(TextToSend)
        bot.send_message(chat_id=chat_id, text=TextToSend[OldLoc:],disable_web_page_preview=True)
    else:
        bot.send_message(chat_id=chat_id, text=TextToSend, disable_web_page_preview=True)

updater = Updater('1115572131:AAE9NmKW2UoBbJq4BZ68UBwUn4jb4MCAvWg')
dp = updater.dispatcher
dp.add_handler(CommandHandler('start',BotStart))
dp.add_handler(CommandHandler('Start',BotStart))
dp.add_handler(MessageHandler(filters.Filters.update, MessageProcessing))
updater.start_polling()
updater.idle