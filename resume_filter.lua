-- resume_filter.lua
function Pandoc(doc)
    local meta = doc.meta
    local new_blocks = {}

    -- 1. Extract NAME (Explicitly check 'name' first, then 'author')
    local name = meta['name'] or meta['author']
    if name then
        -- Convert the metadata object to plain text
        local name_text = pandoc.utils.stringify(name)
        -- Insert as a Level 1 Header (# Name)
        table.insert(new_blocks, pandoc.Header(1, name_text))
        
        -- Remove from metadata so it doesn't appear in the "ugly table"
        meta['name'] = nil
        meta['author'] = nil
    end

    -- 2. Extract ADDRESS
    local address = meta['address']
    if address then
        local combined_inlines = {}
        
        -- Helper to collect all address text into one block
        local function collect_text(addr)
            local t = pandoc.utils.type(addr)
            if t == 'Inlines' then
                for _, inline in ipairs(addr) do table.insert(combined_inlines, inline) end
                table.insert(combined_inlines, pandoc.LineBreak()) 
            elseif t == 'List' then
                for _, item in ipairs(addr) do collect_text(item) end
            elseif t == 'Blocks' then
                -- If it's already blocks (due to \\), flatten it to inlines
                local flat = pandoc.utils.stringify(addr)
                table.insert(combined_inlines, pandoc.Str(flat))
                table.insert(combined_inlines, pandoc.LineBreak())
            end
        end

        collect_text(address)
        
        if #combined_inlines > 0 then
            table.insert(new_blocks, pandoc.BlockQuote(pandoc.Para(combined_inlines)))
        end
        
        meta['address'] = nil
    end

    -- 3. Append the rest of the document
    for _, block in ipairs(doc.blocks) do
        table.insert(new_blocks, block)
    end

    return pandoc.Pandoc(new_blocks, meta)
end
