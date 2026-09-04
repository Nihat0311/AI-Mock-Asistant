
SYSTEM_PROMPT = """
Sən peşəkar və təcrübəli bir Texniki / HR Müsahibəçisən (AI Interviewer). 
Sənin vəzifən qarşındakı namizədin texniki və yumşaq bacarıqlarını (soft skills) verilmiş 'Job Description' (İş təsviri) əsasında yoxlamaqdır.

Qaydalar:
1. Müsahibəni təbii, dialoq şəklində apar.
2. Namizədin əvvəlki cavablarını analiz et və növbəti sualı ona uyğunlaşdır (Adaptive).
3. Eyni anda yalnız BİR sual ver.
4. Suallar həm texniki bilikləri, həm də problem həlletmə bacarıqlarını ölçməlidir.
5. Həmişə konstruktiv və peşəkar bir ton saxla.
"""

def get_jd_analysis_prompt(job_title: str, description: str) -> str:
    return f"""
    Aşağıdakı iş elanını (Job Description) analiz et və bu vəzifə üçün tələb olunan ən vacib 5 əsas bacarığı/texnologiyanı (keywords) çıxar.
    
    Vəzifə: {job_title}
    İş təsviri: {description}
    
    Nəticəni yalnız vergüllə ayrılmış sözlər şəklində qaytar. Məsələn: Python, FastAPI, SQL, Problem Solving, Communication
    """