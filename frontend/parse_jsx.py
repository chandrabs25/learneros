import re

with open("src/remotion/scenes/AtlasScene.tsx", "r") as f:
    content = f.read()

# very basic tag parser
# find <tag> and </tag>
tags = re.findall(r'<\/?([a-zA-Z0-9_]+)[^>]*>', content)
stack = []
for tag in tags:
    if tag.startswith('/'):
        # closing tag
        t = tag[1:]
        if len(stack) > 0 and stack[-1] == t:
            stack.pop()
        else:
            print(f"Mismatch: trying to close {t} but top of stack is {stack[-1] if stack else 'EMPTY'}")
            break
    elif tag.endswith('/'):
        # Self closing
        pass
    else:
        # Opening tag
        # some tags may be self closing but don't have /> at the end of regex group because regex didn't capture the whole tag properly if it has >
        pass
