-- resume_filter.lua
function Pandoc(doc)
    local meta = doc.meta
    local blocks = doc.blocks
    local new_blocks = {}

    -- 1. Extract NAME
    -- Check 'name' (custom) or 'author' (standard) metadata
    local name = meta['name'] or meta['author']
    if name then
        -- Create a Header Level 1 (# Name)
        table.insert(new_blocks, pandoc.Header(1, name))
        
        -- IMPORTANT: Remove from metadata so the table disappears
        meta['name'] = nil
        meta['author'] = nil
    end

    -- 2. Extract ADDRESS
    local address = meta['address']
    if address then
        -- Address might be a list (if you used \address twice)
        if address.t == 'MetaList' then
            for _, addr in ipairs(address) do
                table.insert(new_blocks, pandoc.BlockQuote(pandoc.Para(addr)))
            end
        else
            -- Or just a single entry
            table.insert(new_blocks, pandoc.BlockQuote(pandoc.Para(address)))
        end
        
        -- IMPORTANT: Remove from metadata so the table disappears
        meta['address'] = nil
    end

    -- 3. Append the rest of the document content
    for _, block in ipairs(blocks) do
        table.insert(new_blocks, block)
    end

    -- Return the modified document
    return pandoc.Pandoc(new_blocks, meta)
end
