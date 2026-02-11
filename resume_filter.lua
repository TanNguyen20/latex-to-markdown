-- resume_filter.lua
function Pandoc(doc)
    local meta = doc.meta
    local new_blocks = {}

    -- 1. Extract NAME
    -- Try 'name' (custom) or 'author' (standard)
    local name = meta['name'] or meta['author']
    if name then
        -- stringify ensures we get clean text for the header
        local name_text = pandoc.utils.stringify(name)
        table.insert(new_blocks, pandoc.Header(1, name_text))
        
        -- Clean up metadata
        meta['name'] = nil
        meta['author'] = nil
    end

    -- 2. Extract ADDRESS
    local address = meta['address']
    if address then
        -- Helper function to process a single address entry
        local function process_addr(addr)
            local addr_type = pandoc.utils.type(addr)
            
            if addr_type == 'Inlines' then
                -- Case A: It's simple text/links -> Wrap in Para -> BlockQuote
                table.insert(new_blocks, pandoc.BlockQuote(pandoc.Para(addr)))
            elseif addr_type == 'Blocks' then
                -- Case B: It contains newlines (\\) -> It's already Blocks -> Wrap in BlockQuote
                table.insert(new_blocks, pandoc.BlockQuote(addr))
            elseif addr_type == 'String' then
                -- Case C: It's a raw string
                table.insert(new_blocks, pandoc.BlockQuote(pandoc.Para(pandoc.Str(addr))))
            else
                -- Fallback: convert whatever it is to Blocks
                table.insert(new_blocks, pandoc.BlockQuote(pandoc.utils.blocks(addr)))
            end
        end

        -- Check if address is a list (MetaList) or single item
        if pandoc.utils.type(address) == 'List' then
            for _, item in ipairs(address) do
                process_addr(item)
            end
        else
            process_addr(address)
        end
        
        -- Clean up metadata
        meta['address'] = nil
    end

    -- 3. Append the rest of the document
    -- We use a loop to append blocks to ensure table integrity
    for _, block in ipairs(doc.blocks) do
        table.insert(new_blocks, block)
    end

    return pandoc.Pandoc(new_blocks, meta)
end
