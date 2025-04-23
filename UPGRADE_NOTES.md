# Upgrade Notes

## Anthropic SDK Version Update

### Issue
The application was encountering the following error when using the `/upload-claude/` endpoint:

```
AttributeError: 'Anthropic' object has no attribute 'messages'
```

### Cause
This error occurred because the code in `claude_integration.py` was using the newer Anthropic SDK API style with `client.messages.create()`, but the installed version (specified as `anthropic>=0.5.0` in requirements.txt) might not have supported this method.

### Solution
The requirements.txt file has been updated to specify `anthropic>=0.7.0`, which supports the `messages.create()` method used in the code.

### How to Fix
1. Update your installed packages by running:
   ```
   pip install -r requirements.txt
   ```

2. This will install a newer version of the Anthropic SDK that supports the API calls used in the code.

### Testing
A test script has been provided to verify that the Claude integration works correctly:
```
python test_claude_integration.py
```

This script will attempt to call the Claude API with a simple test image to ensure that the integration is working properly.

### Additional Notes
- Make sure your `.env` file contains a valid `ANTHROPIC_API_KEY`.
- The Claude 3 Sonnet model used in this application requires a valid API key with access to the model.