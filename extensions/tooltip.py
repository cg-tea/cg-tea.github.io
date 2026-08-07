import xml.etree.ElementTree as ET
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor

# This bs extension is to handle the edge case where tooltips contain no URL.
# By default, clicking on them reloads the page. Which is annoying af. 
# Defining an extension (loaded by the hooks.py script in the root folder) allows us to define the desired behavior.

# Matches: [text]("this is a tooltip")
# allows for optional spaces inside the parentheses surrounding the quotes
# Gemini came up with this monster of a regex cause I could never
TOOLTIP_REGEX = r'\[([^\]]+)\]\(\s*["\']([^"\']+)["\']\s*\)'

class DeadLinkTooltipProcessor(InlineProcessor):
    def handleMatch(self, m, data):
        visible_text = m.group(1)  # e.g., "My text that needs a tooltip"
        tooltip_text = m.group(2)  # e.g., "The amazing tooltip text, lot of yapping here"
        
        # Create an anchor (link) element
        el = ET.Element('a')
        # el = ET.Element('span') # this requires additional css to match the link style

        el.set('href', 'javascript:void(0);') # Do nothing when click happens
        el.set('title', tooltip_text)
        el.text = visible_text
        
        return el, m.start(0), m.end(0)

class DeadLinkTooltipExtension(Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(
            DeadLinkTooltipProcessor(TOOLTIP_REGEX, md), 
            'dead_link_tooltip', 
            175
        )