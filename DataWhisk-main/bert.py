import json
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from sklearn.feature_extraction.text import CountVectorizer
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# Function to extract keywords using CountVectorizer
def extract_keywords(reviews, top_n=10):
    vectorizer = CountVectorizer(stop_words='english', max_features=top_n)
    X = vectorizer.fit_transform(reviews)
    keywords = vectorizer.get_feature_names_out()
    frequencies = X.toarray().sum(axis=0)
    return {keyword: int(frequency) for keyword, frequency in zip(keywords, frequencies)}

# Function to generate a word cloud from reviews
def generate_word_cloud(reviews):
    text = ' '.join(reviews)
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.show()

# Function to perform aspect-based sentiment analysis
def aspect_sentiment(review, tokenizer, model):
    aspects = {"food": 3, "service": 3, "atmosphere": 3, "pricing": 3}  # Neutral default
    if not review:
        return aspects

    # Check for specific keywords related to each aspect
    aspect_keywords = {
        "food": ["food", "pie", "meat", "zaatar", "cheese"],
        "service": ["service", "staff", "friendly", "fast"],
        "atmosphere": ["atmosphere", "seating", "space"],
        "pricing": ["price", "affordable", "expensive", "cash"]
    }

    for aspect, keywords in aspect_keywords.items():
        for keyword in keywords:
            if keyword.lower() in review.lower():
                tokens = tokenizer.encode(review, return_tensors='pt', truncation=True, max_length=512)
                result = model(tokens)
                aspects[aspect] = int(torch.argmax(result.logits)) + 1
                break

    return aspects

# Function to provide actionable insights based on aspect ratings
def provide_improvement_suggestions(aspect_averages, df, threshold=3.5):
    suggestions = {}
    for aspect, avg_rating in aspect_averages.items():
        if avg_rating < threshold:
            # Extract negative reviews related to this aspect
            negative_reviews = df[df[aspect] <= threshold]['review'].dropna().tolist()
            keywords = extract_keywords(negative_reviews, top_n=5)
            suggestions[aspect] = {
                "average_rating": avg_rating,
                "keywords_from_negative_reviews": keywords,
                "suggestion": f"Focus on improving {aspect}. Consider addressing concerns around: {', '.join(keywords.keys())}."
            }
    return suggestions

# Main function
def main():
    # Load the JSON file
    with open('googreview-aladdin-bakery-st-laurent.json', 'r', encoding="utf-8") as f:
        data = json.load(f)

    # Convert JSON data to a Pandas DataFrame
    df = pd.DataFrame(data)

    # Load the sentiment analysis model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained('nlptown/bert-base-multilingual-uncased-sentiment')
    model = AutoModelForSequenceClassification.from_pretrained('nlptown/bert-base-multilingual-uncased-sentiment')

    # Perform aspect-based sentiment analysis
    aspect_sentiments = []
    for review in df['review']:
        aspect_sentiments.append(aspect_sentiment(review, tokenizer, model))

    df_aspects = pd.DataFrame(aspect_sentiments)
    df = pd.concat([df, df_aspects], axis=1)

    # Extract keywords and generate a word cloud
    keywords = extract_keywords(df['review'].dropna().tolist())
    print("Top Keywords:", keywords)
    generate_word_cloud(df['review'].dropna().tolist())

    # Save the results to a new file
    output_file = 'reviews_with_aspects.json'
    df.to_json(output_file, orient='records', indent=2)

    csv_output_file = 'reviews_with_aspects.csv'
    df.to_csv(csv_output_file, index=False)

    print(f"Sentiment analysis with aspects completed. Results saved to:\n- {output_file}\n- {csv_output_file}")

    # Calculate average ratings for each aspect
    aspect_averages = df[['food', 'service', 'atmosphere', 'pricing']].mean().to_dict()

    # Print the average ratings
    print("\nAverage Ratings by Aspect:")
    for aspect, avg_rating in aspect_averages.items():
        print(f"{aspect.capitalize()}: {avg_rating:.2f}")

    # Save the averages to a summary JSON file
    summary_file = 'aspect_rating_summary.json'
    with open(summary_file, 'w') as summary_f:
        json.dump(aspect_averages, summary_f, indent=2)

    print(f"\nAspect rating averages saved to: {summary_file}")

    # Provide improvement suggestions
    suggestions = provide_improvement_suggestions(aspect_averages, df)
    suggestions_file = 'improvement_suggestions.json'
    with open(suggestions_file, 'w') as suggestions_f:
        json.dump(suggestions, suggestions_f, indent=2)

    print("\nImprovement Suggestions:")
    for aspect, suggestion in suggestions.items():
        print(f"{aspect.capitalize()} (Average Rating: {suggestion['average_rating']:.2f}):")
        print(suggestion['suggestion'])
        print("Keywords from Negative Reviews:", ", ".join(suggestion['keywords_from_negative_reviews'].keys()))
    
    print(f"\nImprovement suggestions saved to: {suggestions_file}")

if __name__ == '__main__':
    main()
