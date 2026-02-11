-- resume_filter.lua
function RawBlock(el)
  -- Check if the raw block is a LaTeX command
  if el.format == "latex" then
    -- 1. Match \name{...}
    local name = el.text:match("\\name%{(.-)%}")
    if name then
      -- Convert to Markdown Header 1: # Name
      return pandoc.Header(1, pandoc.Str(name))
    end

    -- 2. Match \address{...}
    local address = el.text:match("\\address%{(.-)%}")
    if address then
      -- Clean up: replace LaTeX line break "\\" with a newline
      address = address:gsub("\\\\", "\n")
      -- Convert to Markdown Blockquote: > Address
      return pandoc.BlockQuote(pandoc.Para(pandoc.Str(address)))
    end
  end
end

-- Also catch these commands if they appear inside other blocks
function RawInline(el)
  if el.format == "latex" then
    local name = el.text:match("\\name%{(.-)%}")
    if name then
      return pandoc.Strong(pandoc.Str(name))
    end
  end
end
