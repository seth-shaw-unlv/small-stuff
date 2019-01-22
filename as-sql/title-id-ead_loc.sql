SELECT title, 
       identifier, 
       ead_location 
FROM resource 
WHERE ead_location IS NOT Null 
AND ead_location LIKE '%ark:%' 
ORDER BY identifier;