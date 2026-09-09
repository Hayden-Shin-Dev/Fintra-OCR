"""Count Qwen text tokens locally; never download assets during inference."""
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def qwen35_tokenizer():
    from tokenizers import Tokenizer
    return Tokenizer.from_file(str(Path(__file__).parent/'assets/qwen35-tokenizer.json'))

def context_budget(model,messages,output_tokens):
    if model.split(':')[0].lower()=='qwen3.5':
        try:
            tokenizer=qwen35_tokenizer()
            text_tokens=sum(len(tokenizer.encode(m['content'],add_special_tokens=False).ids) for m in messages)
            method='qwen35_tokenizer_with_256_frame_reserve'
        except (ImportError,OSError):
            text_tokens=sum(len(m['content'].encode('utf-8')) for m in messages);method='utf8_byte_upper_bound'
    else:
        text_tokens=sum(len(m['content'].encode('utf-8')) for m in messages);method='utf8_byte_upper_bound'
    required=text_tokens+output_tokens+256
    context=next((n for n in (16384,32768) if n>=required),None)
    if context is None:raise ValueError('ocr_input_exceeds_mapping_context_budget')
    return context,{'method':method,'text_tokens':text_tokens,'reserved_output':output_tokens,'required_tokens':required}
