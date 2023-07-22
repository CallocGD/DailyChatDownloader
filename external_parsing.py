from gdparser import GDParser


# Mods are just abusive dictators but I'll give you your 
# little badges here just so I can point you little tyrants
AUTHORITY = {
    1:b"(Mod)", 
    2:b"(Eldermod)"
}


HTML_CSS = """<html>
    <style>
        /* Background objects to load... */
        .Comment_A {
            background-color:#2b4563;
            color:rgb(255, 255, 255);
        }

        .Comment_B {
            background-color:#1d2e42;
            color:rgb(255, 255, 255);
        }

        .Username {
            display:inline-block;
            color:rgb(255, 255, 0);
            font-family: Arial, Helvetica, sans-serif;
            font-size: medium;
            text-indent: 5px;
            line-height: 2em    
        }

        .Content {
            color:rgb(255, 255, 255);
            font-family: Arial, Helvetica, sans-serif;
            font-size: small;
            text-indent: 10px;
            /* min-width: 936px; */
            min-height: 20px;
            line-height: 2em
        }

        .Special {
            color:rgb(75, 255, 75);
            font-family: Arial, Helvetica, sans-serif;
            font-size: small;
            text-indent: 10px;
            /* min-width: 936px; */
            min-height: 20px;
            line-height: 2em
        }

        .time {
            color: rgb(0, 0, 0);
            font-family: Arial, Helvetica, sans-serif;
            text-align:right;
            transform: translate(-3vh,-1vh)
        }

        .votes {
            line-height: 2em;
			float:right;
			color:#ffffff;
			margin-right: 20px;
            font-family: Arial, Helvetica, sans-serif;
        }


        .modbadge {
            width: 2.2%;
            transform: translate(0.5vh,-1vh);
        }

        a#link {
            display:inline-block;
            font-size: small;
            font-family: Arial, Helvetica, sans-serif;
            text-align:right;
            text-indent: 5px;
            margin-bottom:5px;
        }

        .remarks {
            color: rgb(53, 145, 148); 
            font-family: Arial, Helvetica, sans-serif;
            font-size: small;
        }

    </style>
    <title>{title}</title>
        <body style="background-color:#111b27">
            <div class="remarks">Generated Through the DailyChatDownloader GUI Version</div>
            <hr>
        """

# TODO Add links to Commandline version or a downloader of some sort...

HTML_BOTTOM = b'\n\t<hr></body>\n</html>'


def parse_comments(line:bytes):
    return GDParser(line)


def to_html(line:bytes):
    # Creates a pattern to use
    use_a = True 
    
    for comment in parse_comments(line):

        html = b'\t\t<div class="Comment_A">' if use_a == True else b'\t\t<div class="Comment_B">'
        use_a = False if use_a else True

        html += (b'\n\t\t\t\t<div class="Username">' + comment.author)

        html += b" " + AUTHORITY.get(comment.modBadge, b"")
        if comment.likes < 0:
            html += b"        (disliked) "
        elif comment.spam:
            html += b"        (Spam) "

        html += b"</div>\n"
    
        html += b'\n\t\t\t\t<div class="votes"> [ Votes: ' + f"{comment.likes}".encode(errors="replace") + b" ]</div>\n"


        if comment.moderatorChatColor:
            html += b'\t\t\t\t<div class="Special">' + comment.body + b'</div>\n'
        else:
            html += b'\t\t\t\t<div class="Content">' + comment.body + b'</div>\n'
        html += b'\t\t\t\t<div class="time">' + comment.age + b' ago</div>\n\t\t\t'
        html += b'<a id="link" href="https://gdbrowser.com/u/' + comment.authorAccountID + b'">Visit Account #' + comment.authorAccountID + b'</a>\n\t\t</div>\n'

        yield html 







def to_json(line:bytes):
    for p in GDParser(line):
        yield p.as_json

def to_text(line:bytes):
    for comment in GDParser(line):
        l = comment.author
        l += AUTHORITY.get(comment.modBadge, b"")
        l += b": "
        l += comment.body
        l += (b"\tTime:" + comment.age)
        l += (f"\tVotes: {comment.likes}".encode())
        l += (b"\tAccountID:" + comment.authorAccountID)
        l += (b"\tMessageID:" + comment.messageID)
        yield l 



def robtop_string_to_json(file:str):
    output = file + "_json.txt"
    with open(output,"wb") as wb:
        with open(file,"rb") as rb:
            for f in rb:
                if f:
                    for comments in to_json(f.rstrip()):
                        wb.write(comments + b"\n")

def robtop_string_to_text(file:str):
    output = file + "_text.txt"
    with open(output,"wb") as wb:
        with open(file,"rb") as rb:
            for f in rb:
                if f:
                    for comments in to_text(f.rstrip()):
                        wb.write(comments + b"\n")

def robtop_string_to_html(file:str, title:str):
    html_file = file.removesuffix(".txt") + ".html"
    with open(html_file,"wb") as wb:
        wb.write(HTML_CSS.replace("{title}", title.removesuffix(".txt")).encode())
        with open(file,"rb") as rb:
            for f in rb:
                if f:
                    for comments in to_html(f.rstrip()):
                        wb.write(comments)

        # Close Html File...
        wb.write(HTML_BOTTOM)


