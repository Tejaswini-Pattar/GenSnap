import re

def generate_hashtags(text):
    """Generate relevant hashtags based on text"""
    if not text:
        return "#instagram #viral #trending"
    
    # Convert to lowercase and split into words
    words = text.lower().split()
    
    # Remove common stop words and punctuation
    stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    words = [re.sub(r'[^\w\s]', '', word) for word in words if word not in stop_words]
    
    # Common hashtag categories with keywords
    hashtag_dict = {
        'love': ['#love', '#instagood', '#photooftheday'],
        'beautiful': ['#beautiful', '#pretty', '#stunning'],
        'happy': ['#happy', '#joy', '#happiness'],
        'sad': ['#sad', '#emotional', '#deep'],
        'nature': ['#nature', '#outdoors', '#scenery', '#naturelovers'],
        'sunset': ['#sunset', '#goldenhour', '#dusk', '#sunsetlover'],
        'sunrise': ['#sunrise', '#morningvibes', '#dawn'],
        'beach': ['#beach', '#ocean', '#seaside', '#beachlife'],
        'mountain': ['#mountains', '#hiking', '#adventure', '#mountainview'],
        'city': ['#citylife', '#urban', '#cityscape', '#citylights'],
        'art': ['#art', '#digitalart', '#creative', '#artwork'],
        'photography': ['#photography', '#photooftheday', '#instaphoto', '#photographer'],
        'food': ['#food', '#foodie', '#delicious', '#foodporn'],
        'travel': ['#travel', '#wanderlust', '#explore', '#travelgram'],
        'fashion': ['#fashion', '#style', '#outfit', '#fashionista'],
        'music': ['#music', '#melody', '#vibes', '#musician'],
        'fitness': ['#fitness', '#workout', '#gym', '#fitlife'],
        'business': ['#business', '#entrepreneur', '#success', '#motivation'],
        'technology': ['#tech', '#innovation', '#digital', '#technology'],
        'family': ['#family', '#familytime', '#love', '#familyfirst'],
        'friends': ['#friends', '#friendship', '#squad', '#bff'],
        'weekend': ['#weekend', '#weekendvibes', '#chill', '#weekendmood'],
        'morning': ['#morning', '#goodmorning', '#morningvibes', '#morningroutine'],
        'night': ['#night', '#nightvibes', '#midnight', '#nightphotography'],
        'winter': ['#winter', '#snow', '#cold', '#winterwonderland'],
        'summer': ['#summer', '#sun', '#hot', '#summervibes'],
        'spring': ['#spring', '#flowers', '#bloom', '#springtime'],
        'autumn': ['#autumn', '#fall', '#leaves', '#autumnvibes'],
        'dog': ['#dog', '#puppy', '#dogsofinstagram', '#doglover'],
        'cat': ['#cat', '#kitty', '#catsofinstagram', '#catlover'],
        'ai': ['#AI', '#artificialintelligence', '#aigenerated', '#digitalart']
    }
    
    # Collect hashtags based on keywords
    hashtags = set()
    
    # Add hashtags from keyword matching
    for word in words:
        if len(word) > 3:  # Only consider words with length > 3
            for key, tags in hashtag_dict.items():
                if key in word or word in key:
                    for tag in tags:
                        hashtags.add(tag)
    
    # Add AI-related hashtags for generated images
    hashtags.update(['#AIgenerated', '#digitalcreation', '#instadaily', '#picoftheday'])
    
    # Add trending hashtags if we have fewer than 10
    if len(hashtags) < 10:
        trending = ['#viral', '#trending', '#explorepage', '#instagram', '#followme']
        hashtags.update(trending[:10 - len(hashtags)])
    
    # Limit to 20 hashtags maximum
    hashtags = list(hashtags)[:20]
    
    return ' '.join(hashtags)

def extract_keywords(text, num_keywords=5):
    """Extract important keywords from text for hashtag generation"""
    # Simple keyword extraction based on frequency
    words = text.lower().split()
    
    # Remove stop words and short words
    stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
    words = [word for word in words if word not in stop_words and len(word) > 3]
    
    # Count frequency
    freq = {}
    for word in words:
        word = re.sub(r'[^\w\s]', '', word)
        if word:
            freq[word] = freq.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:num_keywords]]