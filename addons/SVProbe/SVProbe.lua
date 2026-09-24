-- SVProbe: one-off test for the Forever beta "SavedVariables never loaded" bug.
-- Main chunk runs before native SavedVariables are applied, so a non-nil global
-- here can only come from !!ForeverCompat seeds. Native load lands before ADDON_LOADED.
-- If !!ForeverCompat already seeded a value, clear it here: only the client's own
-- SavedVariables load (which happens after this chunk) can repopulate it.
local preAcct, preChar = SVProbeAcct ~= nil, SVProbeChar ~= nil
SVProbeAcct, SVProbeChar = nil, nil
local postAcct, postChar

local function verdict(pre, post)
    local seed = pre and " (seed cleared first)" or ""
    if post then return "|cff00ff00LOADED natively -> bug FIXED|r" .. seed end
    return "|cffff4040nil -> bug still present|r" .. seed
end

local function report(tag)
    print(("|cff33ff99SVProbe|r [%s] account: %s | per-character: %s"):format(
        tag, verdict(preAcct, postAcct), verdict(preChar, postChar)))
end

local f = CreateFrame("Frame")
f:RegisterEvent("ADDON_LOADED")
f:RegisterEvent("PLAYER_LOGIN")
f:SetScript("OnEvent", function(_, event, name)
    if event == "ADDON_LOADED" then
        if name ~= "SVProbe" then return end
        postAcct, postChar = SVProbeAcct ~= nil, SVProbeChar ~= nil
        SVProbeAcct = SVProbeAcct or {}
        SVProbeChar = SVProbeChar or {}
        SVProbeAcct.marker = "written by client " .. date("%Y-%m-%d %H:%M")
        SVProbeChar.marker = SVProbeAcct.marker
        f:UnregisterEvent("ADDON_LOADED")
    elseif event == "PLAYER_LOGIN" then
        report("login")
        f:UnregisterEvent("PLAYER_LOGIN")
    end
end)

SLASH_SVPROBE1 = "/svprobe"
SlashCmdList.SVPROBE = function() report("manual") end
