"""
Rate Limiter (Step 12)

এই ফাইলে শুধু একটা shared `limiter` object আছে - এটা আলাদা ফাইলে
রাখার কারণ হলো circular import এড়ানো। main.py এই limiter সেটাপ
করে app এ যোগ করে, আবার upload.py/vectorize.py এর মতো route
ফাইলগুলোও এই একই limiter ব্যবহার করে নির্দিষ্ট endpoint এ rate
limit বসায় - দুই জায়গা থেকেই এই ফাইলটা import করা হয়।
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# key_func=get_remote_address মানে প্রতিটা IP address আলাদাভাবে ট্র্যাক হবে
limiter = Limiter(key_func=get_remote_address)
