# Quick Reference: Hardened Prompts

## Expected Output Format

The AI agent **ALWAYS** returns this exact JSON structure:

```json
{
  "is_available": true,
  "sections": [
    {
      "section_id": "0201",
      "open_seats": 3,
      "total_seats": 30,
      "waitlist": 5
    }
  ],
  "raw_text_summary": "Found section 0201 with 3 open seats out of 30 total, and 5 people on the waitlist."
}
```

## Critical Guarantees

✓ Output is **always valid JSON**  
✓ No markdown code blocks or extra text  
✓ `is_available` is always `true` or `false` (never `True`/`False`)  
✓ All numeric fields are numbers (never strings)  
✓ `sections` array can be empty `[]` but field must exist  
✓ All required fields always present  

## Field Validation

### is_available
- **Type**: Boolean
- **Value**: `true` ONLY if user's condition is unambiguously met
- **Default**: `false` (when in doubt)
- **Never**: `"true"`, `True`, `"false"`, `False`

### sections
- **Type**: Array of objects
- **Min length**: 0 (empty array OK)
- **Each object must have**:
  - `section_id`: string (e.g., `"0201"`)
  - `open_seats`: integer ≥ 0
  - `total_seats`: integer > 0
  - `waitlist`: integer ≥ 0

### raw_text_summary
- **Type**: String
- **Length**: 1-3 sentences
- **Content**: Factual summary of findings
- **Tone**: Clear explanation of what was found and why

## Error Scenarios

| Scenario | `is_available` | `sections` | Summary |
|----------|---|---|---|
| Page text is empty | `false` | `[]` | "No content to analyze" |
| No user instructions | `false` | `[]` | "Instructions missing" |
| Section data unclear | `false` | `[]` | "Could not clearly determine availability" |
| Ambiguous seat counts | `false` | `[]` | "Data insufficient or unclear" |
| Non-numeric seat data | `false` | `[]` | "Could not parse seat information" |

## Execution Steps (Model's Internal Process)

1. **UNDERSTAND** - Parse user's condition
2. **LOCATE** - Find section identifiers in page text
3. **EXTRACT** - Pull out numeric seat data
4. **EVALUATE** - Check if condition is met
5. **BUILD** - Create JSON output

## Example Outputs

### Example 1: Seats Available
```json
{
  "is_available": true,
  "sections": [
    {
      "section_id": "0201",
      "open_seats": 2,
      "total_seats": 30,
      "waitlist": 0
    },
    {
      "section_id": "0202",
      "open_seats": 1,
      "total_seats": 25,
      "waitlist": 3
    }
  ],
  "raw_text_summary": "Two sections have open seats: 0201 with 2 available and 0202 with 1 available."
}
```

### Example 2: No Seats, Ambiguous Data
```json
{
  "is_available": false,
  "sections": [],
  "raw_text_summary": "No section data could be clearly extracted from the page text."
}
```

### Example 3: Specific Section Not Found
```json
{
  "is_available": false,
  "sections": [
    {
      "section_id": "0201",
      "open_seats": 0,
      "total_seats": 30,
      "waitlist": 5
    }
  ],
  "raw_text_summary": "Section 0201 exists but has no open seats currently."
}
```

## Testing Checklist

- [ ] Output is valid JSON (can be parsed)
- [ ] `is_available` is boolean
- [ ] `sections` is an array
- [ ] No markdown code blocks in output
- [ ] No extra text before/after JSON
- [ ] All numeric fields are numbers (not strings)
- [ ] Empty sections array returns `false` with empty array
- [ ] All fields present in output

## Integration Notes

- Pydantic AI automatically validates output against `AvailabilityCheck` schema
- Error handling returns safe default: `is_available=false, sections=[], summary="Analysis failed"`
- No breaking changes to existing integrations
- Compatible with both Anthropic and OpenAI providers

## Support

If outputs don't match this format:
1. Check logs for parsing errors
2. Verify page text is being provided
3. Ensure user instructions are clear and specific
4. Check for truncation warnings (>15KB text)

