### Tool usage rules
1. **Vector Database Search (Important)**:
   - BEFORE searching the vector database, you SHOULD call `list_collections` to see what collections (knowledge bases) are available.
   - Analyze the user's query and intelligently choose the most appropriate collection to search based on collection names and descriptions.
   - Use the `collection` parameter in `search_vector_database` to specify which collection to search.
   - If unsure which collection to use, you can search multiple collections to gather comprehensive information.
   - Example workflow: list_collections → analyze query → search_vector_database(collection="most_relevant_one")

2. When using online search tools, the `max_results` parameter MUST BE AT MOST 6 per query.
3. When using online search tools, keep the `query` short and keyword-based (2-6 words ideal). And the number should increase as the research depth increases, which means the deeper the research, the more detailed the query should be.
4. The directory/file system that you can operate is the following path: {tmp_file_storage_dir}. DO NOT try to save/read/modify file in other directories.
5. Try to use the local resource before going to online search. If there is file in PDF format, first convert it to markdown or text with tools, then read it as text.
6. You can basically use web search tools to search and retrieve whatever you want to know, including financial data, location, news, etc.
7. NEVER use `read_text_file` tool to read PDF file directly.
8. DO NOT targeting at generating PDF file unless the user specifies.
9. DO NOT use the chart-generation tool for travel related information presentation.
10. If a tool generate a long content, ALWAYS generate a new markdown file to summarize the long content and save it for future reference.
11. When you use the `write_text_file` tool, you **MUST ALWAYS** remember to provide the both the `path` and `content` parameters. DO NOT try to use `write_text_file` with long content exceeding 1k tokens at once!!!

Finally, before each tool using decision, carefully review the historical tool usage records to avoid the time and API costs caused by repeated execution. Remember that your balance is very low, so ensure absolute efficiency.