# Chapter 2: Literature Review

## Odradek — A Feedback Loop and Insights Management Platform

This chapter reviews the academic literature underpinning the design and implementation of Odradek, a platform for capturing, analyzing, and acting on customer signals. The review is organized around eleven thematic areas that correspond to the platform's core capabilities: voice of the customer programs, sentiment analysis, business intelligence pipelines, anomaly detection, decision support and automation, experimental design, churn prediction, data integration, information visualization, workflow management, and organizational learning.

---

## 2.1 Customer Feedback Management and Voice of the Customer (VoC)

### 2.1.1 Voice of the Customer Programs

The concept of Voice of the Customer was formalized by Griffin and Hauser (1993) in their seminal paper "The Voice of the Customer" published in *Marketing Science*. They defined VoC as a structured process for capturing customer needs and translating them into product and service attributes, proposing a methodology grounded in contextual interviews and hierarchical need structuring. Their work established that 20–30 in-depth interviews could capture over 90% of customer needs within a segment, a finding that shaped VoC practice for decades.

VoC programs evolved significantly through the quality management tradition. Gaskin, Griffin, Hauser, Katz, and Klein (2010) extended the original framework in *Journal of Product Innovation Management*, demonstrating how VoC data could be integrated with conjoint analysis for product development prioritization. The digital transformation of VoC began in earnest in the 2010s. Blazevic, Hammedi, Garnefeld, Rust, Keiningham, Andreassen, Donthu, and Carl (2013), writing in the *Journal of Service Management*, examined how firms could harness online customer engagement as a form of continuous VoC, moving beyond episodic survey-based collection.

Modern VoC programs are characterized by what Lemon and Verhoef (2016) describe in the *Journal of Marketing* as multi-touchpoint journey monitoring. Their customer experience framework positions VoC not as a discrete research activity but as an ongoing organizational capability. The Odradek platform embodies this evolution directly: rather than treating VoC as periodic market research, it implements continuous signal capture across NPS, CSAT, CES, support tickets, social mentions, and behavioral analytics, operationalizing the always-on VoC paradigm that the literature now advocates.

### 2.1.2 Customer Feedback Loops

The concept of closed-loop feedback systems in customer management draws from both systems theory and service operations. Wirtz, Tambyah, and Mattila (2010), in the *Journal of Service Research*, demonstrated that organizations with formal feedback response mechanisms achieved significantly higher customer retention than those that merely collected feedback. Their work highlighted what subsequent researchers have termed the "feedback-action gap" — the persistent organizational failure to translate collected feedback into operational changes.

Bone, Lemon, Voorhees, Liljenquist, Fombelle, Detienne, and Money (2017) explored this gap in *Journal of Marketing Research*, finding that fewer than 30% of firms systematically close the loop on customer feedback. They identified structural barriers including departmental silos, unclear ownership, and the absence of workflow systems to route feedback to responsible teams. Kumar, Pozza, and Ganesh (2013) argued in *Journal of Retailing* that feedback loop effectiveness depends on integrating customer data across functions, not merely collecting it.

Odradek addresses these documented challenges through its rules engine and action logging architecture. By enabling conditional automation rules that trigger actions based on feedback signals, and maintaining an audit trail of executed actions, the platform provides the structural mechanisms that Bone et al. identified as missing in most organizations.

### 2.1.3 Net Promoter Score (NPS)

Reichheld (2003) introduced the Net Promoter Score in *Harvard Business Review*, arguing that a single loyalty question was the strongest predictor of revenue growth. This claim generated substantial academic debate. Keiningham, Cooil, Andreassen, and Aksoy (2007) published a rigorous critique in *Journal of Marketing*, demonstrating through longitudinal data that NPS was not superior to other satisfaction measures in predicting business outcomes such as same-store sales growth.

Despite academic skepticism, NPS achieved widespread industry adoption. De Haan, Verhoef, and Wiesel (2015) offered a more nuanced perspective in *International Journal of Research in Marketing*, showing that the predictive validity of NPS varies by industry and that its value lies partly in its organizational simplicity as a rallying metric. Morgan and Rego (2006) in *Marketing Science* similarly found that while NPS correlates with business performance, it does not consistently outperform alternative metrics like customer satisfaction or repurchase likelihood.

The Odradek platform reflects the current best-practice consensus by treating NPS as one signal among many rather than as a singular metric, an approach consistent with Keiningham, Aksoy, Buoye, and Cooil's (2011) recommendation in *Journal of Service Management* for multi-metric customer health assessment.

### 2.1.4 Customer Satisfaction Measurement

Customer satisfaction measurement has a long research tradition. The SERVQUAL model by Parasuraman, Zeithaml, and Berry (1988), published in the *Journal of Retailing*, established the gap-based approach to service quality assessment across five dimensions. While SERVQUAL has been criticized for its disconfirmation paradigm (Cronin & Taylor, 1992, *Journal of Marketing*), it remains foundational.

The Customer Effort Score was introduced by Dixon, Freeman, and Toman (2010) in *Harvard Business Review*, arguing that reducing customer effort is more predictive of loyalty than exceeding expectations. Their subsequent research provided evidence that effort-reducing strategies drive repurchase and reduce negative word-of-mouth more reliably than delight-oriented approaches. This challenged the dominant satisfaction paradigm and introduced a complementary metric to CSAT and NPS.

Fornell, Johnson, Anderson, Cha, and Bryant (1996) established the American Customer Satisfaction Index framework in *Journal of Marketing*, creating a national-level model linking customer expectations, perceived quality, perceived value, satisfaction, complaints, and loyalty. Odradek's multi-metric approach — incorporating NPS, CSAT, and CES simultaneously — aligns with the scholarly consensus that Anderson, Fornell, and Lehmann (1994) articulated in *Journal of Marketing*: customer satisfaction is best understood through converging measures rather than any single indicator.

### 2.1.5 Multi-Channel Feedback Integration

The challenge of integrating feedback across channels has received growing attention. Neslin, Grewal, Leghorn, Shankar, Teerling, Thomas, and Verhoef (2006) published an influential framework in *Journal of Service Research* on multichannel customer management, identifying data integration as a primary operational challenge. Verhoef, Kannan, and Inman (2015) extended this in *Journal of Retailing*, proposing that omnichannel management requires not merely collecting data from multiple channels but synthesizing it into unified customer profiles.

Homburg, Jozic, and Kuehnl (2017) in the *Journal of Marketing* demonstrated that customer experience management across touchpoints requires organizational integration mechanisms, not just technological ones. Their research showed that firms with cross-functional feedback integration achieved superior customer outcomes compared to those with channel-siloed data. Odradek is positioned precisely at this integration challenge, ingesting signals from surveys, support systems, social channels, and behavioral analytics into a unified workspace-scoped data model.

---

## 2.2 Sentiment Analysis and Natural Language Processing for Customer Feedback

### 2.2.1 Foundations of Sentiment Analysis

The systematic study of sentiment analysis emerged as a distinct research area in the early 2000s. Pang, Lee, and Vaithyanathan (2002) demonstrated that machine learning classifiers such as Naive Bayes and Support Vector Machines could classify movie review polarity with accuracy rivaling human-crafted lexicons, establishing the viability of data-driven approaches. Pang and Lee (2008) subsequently published a comprehensive survey in *Foundations and Trends in Information Retrieval* that organized the field around opinion mining, subjectivity detection, and document-level sentiment classification, providing the conceptual taxonomy that continues to guide research.

Liu (2012), in *Sentiment Analysis and Opinion Mining* (Morgan & Claypool), extended this taxonomy to encompass entity-level and aspect-level analysis, formalizing the distinction between document-, sentence-, and feature-level sentiment that is directly relevant to Odradek's multi-granularity classification of customer signals. The evolution from lexicon-based approaches (Taboada et al., 2011, *Computational Linguistics*) through statistical machine learning to contemporary deep learning methods reflects a broader trend toward representations that capture contextual nuance in customer language.

### 2.2.2 Aspect-Based Sentiment Analysis

Customer feedback rarely expresses uniform sentiment; a single review may praise product quality while criticizing delivery speed. Aspect-based sentiment analysis (ABSA) addresses this challenge by identifying specific entities or attributes and associating sentiment with each. The SemEval shared tasks organized by Pontiki et al. (2014, 2015, 2016) at *Proceedings of the International Workshop on Semantic Evaluation* established standardized benchmarks and evaluation protocols for aspect term extraction and aspect-level polarity classification across domains including restaurants and consumer electronics.

Subsequent work by Wang et al. (2016) introduced attention-based neural architectures for ABSA, published in *Proceedings of EMNLP*, enabling models to selectively focus on context words relevant to each aspect. For Odradek, which must decompose multi-faceted customer signals into discrete themes with independent sentiment scores, ABSA provides the theoretical and methodological basis for the platform's theme extraction pipeline.

### 2.2.3 Text Mining and Topic Modeling

The extraction of recurring themes from large feedback corpora relies heavily on topic modeling. Blei, Ng, and Jordan (2003) introduced Latent Dirichlet Allocation (LDA) in the *Journal of Machine Learning Research*, a generative probabilistic model that discovers latent thematic structure in document collections. Tirunillai and Tellis (2014), writing in *Journal of Marketing Research*, demonstrated the extraction of product quality dimensions from user-generated content using topic models. More recent approaches incorporate neural topic models and BERTopic (Grootendorst, 2022), which leverage transformer embeddings for more coherent topic discovery.

### 2.2.4 Confidence Scoring and Classifier Calibration

When Odradek assigns confidence scores alongside sentiment labels, it engages with the research literature on probabilistic calibration. Guo et al. (2017), in *Proceedings of ICML*, demonstrated that modern deep neural networks are often poorly calibrated, producing overconfident predictions. Temperature scaling and Platt scaling (Platt, 1999) remain widely used post-hoc calibration techniques. For customer feedback platforms, well-calibrated confidence scores are operationally significant: they determine whether a signal is automatically routed or flagged for human review.

### 2.2.5 Transformer-Based Approaches

The advent of transformer architectures (Vaswani et al., 2017, *Proceedings of NeurIPS*) fundamentally transformed NLP. BERT (Devlin et al., 2019, *Proceedings of NAACL*) introduced bidirectional pre-training, achieving state-of-the-art results on sentiment benchmarks. Sun, Huang, and Qiu (2019) demonstrated that fine-tuning BERT for sentiment analysis with domain-specific data yields substantial improvements. The GPT family (Brown et al., 2020) demonstrated few-shot and zero-shot capabilities relevant to feedback analysis in low-resource settings.

### 2.2.6 Mixed Sentiment and Urgency Detection

Customer feedback frequently contains conflicting sentiments across different aspects. Wilson, Wiebe, and Hoffmann (2005), in *Proceedings of HLT-EMNLP*, distinguished between prior polarity and contextual polarity, showing that negation, hedging, and discourse structure can invert or attenuate sentiment. Odradek's inclusion of a "mixed" sentiment category reflects the practical reality that binary or ternary classification schemes oversimplify customer expression.

Beyond sentiment, the automatic triage of customer feedback requires detecting urgency and complaint severity. Gupta et al. (2020), in *Proceedings of EMNLP*, explored priority detection in customer service dialogues using multi-task learning. For Odradek, which routes signals based on severity levels (low, medium, high, critical), this literature provides the basis for automated escalation and triage workflows.

---

## 2.3 Signal-to-Insight Pipelines and Business Intelligence

### 2.3.1 Business Intelligence Evolution

The field of business intelligence has undergone substantial transformation. Chaudhuri, Dayal, and Narasayya (2011), writing in *Communications of the ACM*, provided a foundational overview of BI technologies encompassing data warehousing, OLAP, and analytics platforms. The subsequent shift toward self-service BI was documented by Alpar and Schulz (2016) in *Business & Information Systems Engineering*, who observed that business users increasingly demanded direct analytical access without IT intermediation. Real-time BI has emerged as a critical capability; Sahay and Ranjan (2008) explored the architectural requirements for streaming analytics.

Odradek reflects this evolutionary trajectory: it embeds analytics directly into the workflow of product, customer experience, and marketing teams, providing real-time KPI dashboards and automated insight delivery rather than requiring users to query a separate BI environment.

### 2.3.2 Data-to-Insight Frameworks

The conceptual foundation for transforming raw data into actionable understanding originates with Ackoff's (1989) DIKW hierarchy in the *Journal of Applied Systems Analysis*. Rowley (2007), writing in the *Journal of Information Science*, critically revisited the framework while affirming its conceptual utility. Chen, Chiang, and Storey (2012) published an influential overview in *MIS Quarterly* categorizing business intelligence and analytics into three eras: BI 1.0 (structured data), BI 2.0 (web and unstructured data), and BI 3.0 (mobile and sensor data).

Odradek operationalizes the DIKW hierarchy explicitly: raw customer signals constitute data; aggregated and contextualized signals become information; derived insights with confidence metrics and severity classification represent knowledge; and team-routed action recommendations approach wisdom.

### 2.3.3 Customer Intelligence and Competing on Analytics

Davenport and Harris (2007), in *Competing on Analytics* (Harvard Business School Press), articulated the strategic imperative for organizations to derive competitive advantage from analytical capabilities applied to customer data. LaValle, Lesser, Shockley, Hopkins, and Kruschwitz (2011), publishing findings from an MIT Sloan Management Review and IBM survey, found that top-performing organizations were three times more likely to describe themselves as using analytics to guide future strategies rather than merely justify past decisions.

### 2.3.4 Automated Insight Generation and the Insight-Action Gap

The concept of augmented analytics, where machine learning automates pattern detection and insight generation, was explored by Wang, Kung, and Byrd (2018) in *Decision Support Systems*. Despite advances in analytical capability, the translation of insights into organizational action remains challenging. Ghasemaghaei, Hassanein, and Turel (2017), in *International Journal of Information Management*, empirically demonstrated that data quality and analytical capability alone do not guarantee improved decision-making without organizational mechanisms for insight operationalization. Prescriptive analytics, as defined by Lepenioti, Bousdekis, Apostolou, and Mentzas (2020) in *Journal of Industrial Information Integration*, extends beyond prediction to recommend specific actions.

Odradek addresses the insight-action gap architecturally through its team routing capability, severity classification, and action logging — embedding the insight-to-action pathway directly into the platform's workflow.

---

## 2.4 Anomaly Detection in Customer Metrics

### 2.4.1 Foundations of Anomaly Detection

The foundational survey by Chandola, Banerjee, and Kumar (2009) in *ACM Computing Surveys* established a widely adopted taxonomy of anomalies into three categories: point anomalies (individual data instances deviating from the norm), contextual anomalies (instances anomalous only within a specific context such as time or geography), and collective anomalies (collections of related instances that are jointly anomalous). Aggarwal (2017), in *Outlier Analysis* (Springer), extended this framework by formalizing the distinction between supervised, semi-supervised, and unsupervised anomaly detection paradigms.

### 2.4.2 Time-Series Anomaly Detection

Customer metrics are inherently temporal. Classical approaches rooted in ARIMA modeling (Box, Jenkins, & Reinsel, 2015) detect anomalies as residuals exceeding expected confidence intervals. Taylor and Letham (2018), in *The American Statistician*, introduced Prophet, a decomposable time-series model that handles seasonality, trend changes, and holiday effects, making it particularly suited to business metric monitoring. Statistical process control methods, originating from Shewhart (1931) and refined by Montgomery (2019), provide control chart methodologies that remain widely used for detecting shifts in process means.

### 2.4.3 Machine Learning Approaches

Liu, Ting, and Zhou (2008) introduced isolation forests in *Proceedings of the Eighth IEEE International Conference on Data Mining*, providing an efficient tree-based method that isolates anomalies by exploiting their susceptibility to partitioning. Breunig et al. (2000) proposed the Local Outlier Factor in *Proceedings of the ACM SIGMOD Conference*. More recently, autoencoder-based approaches (Sakurada & Yairi, 2014) detect anomalies through reconstruction error, with deep variants showing particular promise for complex behavioral data.

### 2.4.4 Real-Time Detection and Operational Considerations

Ahmad et al. (2017) presented the Numenta Anomaly Benchmark in *Neurocomputing*, establishing evaluation criteria for streaming anomaly detectors. Bifet and Gavalda (2007) developed ADWIN, an adaptive windowing method for detecting distributional change in data streams. The translation of anomaly detection into actionable alerts requires careful severity calibration to address alert fatigue — a challenge directly relevant to systems like Odradek where multiple correlated signals should be consolidated rather than generating redundant alerts.

---

## 2.5 Decision Support Systems and Rule-Based Automation

### 2.5.1 Decision Support Systems

The conceptual foundations of DSS were established by Gorry and Scott Morton (1971) and formalized by Keen and Scott Morton (1978). Sprague (1980) advanced the field by articulating a three-component DSS architecture comprising a database management subsystem, a model management subsystem, and a dialogue generation subsystem. The evolution from model-driven DSS toward data-driven and knowledge-driven variants has been well documented (Power, 2002; Arnott & Pervan, 2005). Odradek's rule engine operates at this intersection, combining structured conditional logic with data-driven insight properties.

### 2.5.2 Rule-Based Expert Systems

Rule-based expert systems emerged from AI research in the 1970s, most notably through the MYCIN system for bacterial infection diagnosis (Shortliffe, 1976; Buchanan & Shortliffe, 1984). The Rete algorithm (Forgy, 1982) provided efficient pattern matching for forward-chaining inference engines. Odradek's FeedbackRules employ forward-chaining logic: when incoming insight properties satisfy rule conditions, corresponding actions are triggered.

### 2.5.3 Business Rules Management

The business rules approach, articulated by Ross (2003), advocates externalizing decision logic from procedural application code into declarative, human-readable rule statements. Business Rules Management Systems (BRMS) platforms operationalize these principles at enterprise scale (Boyer & Mili, 2011). Odradek's architecture reflects this paradigm by allowing users to define conditions declaratively across multiple insight dimensions and to specify resulting actions without modifying underlying application logic.

### 2.5.4 Automated Decision-Making and Human-in-the-Loop

Parasuraman, Sheridan, and Wickens (2000) proposed a ten-level taxonomy of automation. Lee and See (2004) demonstrated that trust in automation is calibrated through perceived reliability, predictability, and process transparency. Odradek addresses this tension by supporting dual execution modes: fully automated action execution for high-confidence, routine decisions, and manual approval workflows where human judgment is required.

### 2.5.5 Multi-Criteria Decision Analysis and Prescriptive Analytics

Saaty's (1980) Analytic Hierarchy Process introduced pairwise comparison for deriving criterion weights. Prescriptive analytics extends beyond the descriptive and predictive tiers to recommend specific actions (Delen & Demirkan, 2013; Bertsimas & Kallus, 2020; Lepenioti et al., 2020). Odradek's FeedbackRules constitute a prescriptive layer: given predictive insight properties, the system prescribes specific organizational actions.

---

## 2.6 A/B Testing, Experimental Design, and Organizational Learning from Experiments

### 2.6.1 Online Controlled Experiments

The foundation of modern A/B testing was formalized by Kohavi, Longbotham, Sommerfield, and Henne (2009) in *Data Mining and Knowledge Discovery*. Kohavi, Tang, and Xu (2020) consolidated two decades of practice in *Trustworthy Online Controlled Experiments* (Cambridge University Press), documenting lessons from running experiments at Microsoft, Google, and Amazon. Their work emphasizes that even small measured effects, when applied at scale, can yield substantial business value — a principle directly relevant to Odradek's tracking of average lift percentage across accumulated learnings.

### 2.6.2 Statistical Foundations

The statistical underpinnings rest on the Neyman-Pearson hypothesis testing framework. Deng, Xu, Kohavi, and Walker (2013) advanced variance reduction techniques that improved statistical power without increasing sample size. Cohen (1988), in *Statistical Power Analysis for the Behavioral Sciences*, established the canonical framework for effect size measurement and power analysis. Odradek's storage of confidence levels and sample sizes for each learning directly operationalizes these statistical concepts.

### 2.6.3 Meta-Analysis and Practical Challenges

When organizations accumulate dozens of experiments, meta-analysis becomes applicable. Borenstein, Hedges, Higgins, and Rothstein (2009) formalized methods for combining effect sizes across independent studies. Practitioners face numerous pitfalls: Johari, Koomen, Pekelis, and Walsh (2017) demonstrated how continuous monitoring inflates false positive rates. Simpson's paradox, multiple comparisons problems, and novelty effects all require careful management.

### 2.6.4 Learning from Experiments

Thomke (2003), in *Experimentation Matters* (Harvard Business School Press), argued that organizations capable of rapid experimentation develop superior innovation capabilities. The concept of a "learning repository," which Odradek instantiates through its AbLearning model with winning and losing variant examples, aligns with what Argote (2013) described as the encoding of experiential knowledge into organizational memory.

### 2.6.5 Digital Marketing Experimentation

Email marketing experimentation has substantial applied literature. Sahni, Wheeler, and Chintagunta (2018), in *Marketing Science*, demonstrated that personalized subject lines significantly increase open rates. Bleier and Eisenbeiss (2015), in the *Journal of Marketing*, found that deep personalization can increase click-through rates but may trigger reactance when perceived as intrusive. Odradek's coverage of categories like subject lines, CTA text, send time, and personalization reflects the domains where digital experimentation yields the most actionable learnings.

---

## 2.7 Customer Churn Prediction and Prevention

### 2.7.1 Churn Prediction Models

The foundational work on customer defection detection was established by Neslin et al. (2006), who organized a large-scale churn prediction tournament demonstrating that variable selection matters more than technique choice. Logistic regression serves as an interpretable baseline (Lariviere & Van den Poel, 2005), while ensemble methods consistently outperform single classifiers (Verbeke et al., 2012). Survival analysis offers complementary time-to-event framing (Lu, 2002).

### 2.7.2 Deep Learning and Early Warning Systems

Recurrent architectures such as LSTM networks have proven effective for modeling sequential customer behavior (Jeyakumar et al., 2020). The concept of early warning systems draws on the principle that defection is preceded by observable behavioral shifts. Risselada et al. (2010) found that changes in usage intensity served as reliable leading indicators weeks before formal cancellation. Gattermann-Itschert and Thonemann (2021) demonstrated that proactive early detection systems can reduce churn rates by 10–15%.

### 2.7.3 Customer Lifetime Value

Fader and Hardie's (2005) BG/NBD and Pareto/NBD models established probabilistic methods for estimating future customer value. Gupta et al. (2006) demonstrated that CLV-based segmentation substantially outperforms traditional RFM approaches. Within Odradek, CLV-based prioritization ensures that the platform ranks at-risk customers by the revenue impact of potential loss.

### 2.7.4 Feedback-Based Churn Indicators

De Haan et al. (2015) found that declining CSAT trajectories were more predictive than absolute scores, emphasizing trend detection. Luo and Homburg (2007) demonstrated that complaint intensity and resolution failure are strong negative predictors of retention. Odradek synthesizes attitudinal signals alongside behavioral data, monitoring NPS trajectories, sentiment shifts, and escalation patterns.

### 2.7.5 Intervention Strategies and Multi-Signal Detection

Ascarza (2018) argued that targeting customers with the highest churn probability can be counterproductive if those customers are unresponsive to intervention, advocating for targeting "persuadable" segments. Uplift modeling has emerged as the methodologically preferred approach (Devriendt et al., 2018). Verbeke et al. (2012) demonstrated that feature engineering across multiple data domains improved model performance beyond any single-source approach — a multi-signal philosophy central to Odradek's design.

---

## 2.8 Multi-Source Data Integration and Fusion

### 2.8.1 Data Integration Foundations

Lenzerini (2002) established the distinction between Global-as-View and Local-as-View approaches in data integration. Schema matching was comprehensively surveyed by Rahm and Bernstein (2001) in the *VLDB Journal*. The Extract-Transform-Load paradigm remains dominant (Vassiliadis et al., 2002), though modern platforms increasingly adopt ELT variants (Kimball & Ross, 2013). Odradek's normalization of qualitative feedback and quantitative metrics into a common signal schema represents a practical instantiation of mediated schema integration.

### 2.8.2 Data Fusion and Customer Data Platforms

Bleiholder and Naumann (2008) provided a comprehensive taxonomy of fusion strategies in *ACM Computing Surveys*. Dong and Srivastava (2015) advanced truth discovery methods in *Big Data Integration*. The concept of a 360-degree customer view has evolved from early CRM research through modern Customer Data Platforms (Eckerson & White, 2019). Identity resolution remains a core technical challenge (Christen, 2012).

### 2.8.3 API-Based and Event-Driven Integration

Fielding (2000) established REST as the dominant architectural style. Hohpe and Woolf (2003), in *Enterprise Integration Patterns*, catalogued messaging patterns that underpin webhook and event-driven architectures. Odradek's integration architecture, supporting webhooks, API polling, and direct connectors, embodies a hybrid topology combining push-based and pull-based ingestion patterns.

### 2.8.4 Data Quality and Governance

Batini et al. (2009) provided a comprehensive survey of data quality dimensions in *ACM Computing Surveys*. Abraham, Schneider, and vom Brocke (2019) surveyed data governance frameworks. Odradek implements workspace-scoped data isolation, where all queries filter by workspace_id, enforcing tenant separation consistent with the principle of least privilege and regulatory expectations (GDPR Article 30).

---

## 2.9 Dashboard Design and Information Visualization

### 2.9.1 Dashboard Design Principles

Few (2006) established foundational principles for information dashboard design, emphasizing that effective dashboards must reduce cognitive load by presenting data in compact, meaningful visual forms. Tufte (1983, 2001) contributed the influential concepts of data-ink ratio and chartjunk minimization. These principles align with cognitive load theory (Sweller, 1988). Odradek's use of discrete KPI cards with single-metric focus reflects Few's recommendation to present key information in isolated, scannable units.

### 2.9.2 Information Visualization Theory

Shneiderman's (1996) visual information seeking mantra — "overview first, zoom and filter, then details-on-demand" — remains the dominant interaction paradigm. Card, Mackinlay, and Shneiderman (1999) formalized the reference model for visualization. Munzner (2014) proposed a nested model for visualization design and validation. Odradek's architecture, progressing from raw signals through derived insights to actionable workflows, mirrors this multi-level abstraction.

### 2.9.3 Color Encoding and Accessibility

Ware (2004, 2012) detailed the perceptual basis of color encoding. Harrower and Brewer (2003) developed ColorBrewer, providing empirically validated color palettes. Odradek employs semantic color mapping for severity levels and sentiment polarity. Machado et al. (2009) demonstrated that approximately 8% of males experience color vision deficiency, underscoring the need for redundant encoding alongside color.

### 2.9.4 Funnel and Kanban Visualization

Anderson (2010) formalized Kanban as a method for knowledge work management, emphasizing visualization of workflow states and limitation of work in progress. Odradek's insight status funnel tracks progression through states from new through resolved, applying conversion funnel paradigms (Kohavi et al., 2009) to customer feedback management.

### 2.9.5 Chart Type Selection

Cleveland and McGill (1984) established a hierarchy of graphical perception accuracy. For temporal data, area charts effectively communicate cumulative trends (Heer et al., 2009). Sarikaya and Gleicher (2018) argued that chart type selection should be task-dependent rather than dogmatic, supporting Odradek's pragmatic approach to visualization design.

---

## 2.10 Workflow Automation and Business Process Management

### 2.10.1 BPM Foundations

Van der Aalst (2013) defines BPM as the convergence of process modeling, workflow management, and process mining into a unified lifecycle. Van der Aalst, ter Hofstede, Kiepuszewski, and Barros (2003) catalogued twenty fundamental workflow patterns in *Distributed and Parallel Databases*. Odradek's linear insight status progression with branching states exemplifies several of these patterns, notably sequential routing with deferred choice.

### 2.10.2 Workflow Management and State Machines

The WfMC Reference Model (Hollingsworth, 1995) defined five interfaces for interoperable workflow systems. Harel's (1987) statecharts provide the theoretical basis for the finite state machine governing Odradek's InsightStatus type. Reichert and Weber (2012) extended this thinking to adaptive workflows that accommodate runtime changes.

### 2.10.3 Process Automation

Early RPA, as surveyed by van der Aalst, Bichler, and Heinzl (2018) in *Business & Information Systems Engineering*, focused on automating structured, rule-based tasks. Odradek's FeedbackRule model, with its condition-action structure and auto_execute flag, embodies this paradigm. More recent intelligent process automation extends RPA with machine learning capabilities (Syed et al., 2020, *Computers in Industry*).

### 2.10.4 Human-in-the-Loop and Compliance

Russell, van der Aalst, ter Hofstede, and Edmond (2005) identified resource patterns including delegation, escalation, and approval. Dellermann, Ebel, Sollner, and Leimeister (2019) argue that effective systems must balance algorithmic efficiency with human judgment. Accorsi (2009) provided a formal framework for business process auditing emphasizing completeness, tamper-evidence, and temporal ordering — properties satisfied by Odradek's ActionLog model.

### 2.10.5 Team Routing and Process Mining

Kumar, van der Aalst, and Verbeek (2002) formalized work distribution as an optimization problem involving role-based and skill-based assignment. Van der Aalst's (2016) *Process Mining* established methods for reconstructing actual process behavior from event logs. Odradek's combination of timestamped action logs and status transitions creates the event data necessary for such analysis.

---

## 2.11 Knowledge Management and Organizational Learning

### 2.11.1 Knowledge Management Foundations

Nonaka and Takeuchi (1995), in *The Knowledge-Creating Company*, established the SECI model describing four modes of knowledge conversion: Socialization, Externalization, Combination, and Internalization. Polanyi's (1966) distinction between tacit and explicit knowledge provides the epistemological basis. Alavi and Leidner (2001, *MIS Quarterly*) emphasized that knowledge management systems succeed when they support both storage and contextual retrieval.

In Odradek, when A/B test outcomes are codified as AbLearnings with explicit winning and losing patterns, tacit practitioner intuitions are converted into explicit, retrievable organizational knowledge — operationalizing the Externalization phase of the SECI model.

### 2.11.2 Organizational Learning Theory

Argyris and Schon (1978) distinguished between single-loop and double-loop learning. Senge (1990) articulated the "learning organization" concept. March (1991, *Organization Science*) introduced the exploration-exploitation tension. Odradek's insight lifecycle embodies this balance: the system encourages exploitation when validated patterns are applied to recurring problems while supporting exploration when new signals reveal emerging trends.

### 2.11.3 Evidence-Based Management

Pfeffer and Sutton (2006) advocated for evidence-based management. Rousseau (2006, *Academy of Management Review*) formalized the concept drawing parallels to evidence-based medicine. Odradek's closed-loop architecture — signals generate insights, insights drive actions, action outcomes feed back as new signals — directly implements the evidence accumulation cycle.

### 2.11.4 Learning from Failure

Edmondson (1999, *Administrative Science Quarterly*) demonstrated that psychological safety enables teams to report and learn from failures. Cannon and Edmondson (2005) argued that organizations systematically under-invest in failure analysis. Odradek explicitly captures losing A/B test variants alongside winners, institutionalizing the documentation of what did not work — reflecting McGrath's (1999) argument that failed experiments contain information at least as valuable as successes.

### 2.11.5 Collective Intelligence and Cross-Functional Learning

Woolley et al. (2010, *Science*) established that collective intelligence emerges from group composition and interaction patterns. Carlile (2004, *Organization Science*) examined knowledge boundaries across functional domains. Odradek's workspace-scoped architecture and team-routing capabilities facilitate aggregation of insights across functional boundaries.

### 2.11.6 Feedback Loops and Continuous Improvement

Sterman (2000) demonstrated that feedback loops are the fundamental mechanism through which organizations learn and adapt. Deming's (1986) Plan-Do-Study-Act cycle remains the canonical model for continuous improvement. Odradek's signal-to-insight-to-action-to-learning pipeline constitutes a closed-loop learning system that operationalizes these principles.

---

## 2.12 Industry Practitioner Evidence: Analyst and Vendor Perspectives on Feedback Loop Pain Points

The academic literature reviewed in sections 2.1–2.11 is strongly corroborated by recent industry research from major analyst firms and technology vendors. This section synthesizes practitioner-facing evidence that validates the core problems Odradek is designed to address.

### 2.12.1 Gartner: The VoC Platform Market and the Action Gap

Gartner's 2026 Magic Quadrant for Voice of the Customer Platforms (published March 2026) evaluates 12 vendors and identifies a market undergoing fundamental transformation. Gartner notes that AI is moving VoC platforms from structured feedback collection toward proactive, autonomous action — predicting that the next wave will be "AI Experience Agents capable of autonomously assessing customer records and acting on them before a problem escalates" (CXM World, March 2026). Qualtrics holds the top Leader position for the fifth consecutive year, followed by Medallia and Sprinklr. Gartner defines the core VoC platform function as collecting feedback from multiple sources, analyzing it with AI, and turning it into actionable insights — then guiding customer-facing teams with recommendations and prescriptive actions. The fact that Gartner identifies "prescriptive action" as a defining capability validates Odradek's design philosophy of embedding action automation directly into the feedback lifecycle.

Critically, Gartner's Critical Capabilities report evaluated platforms across five use cases, with Qualtrics ranking first across all five. Qualtrics' "Experience Agents" — which close feedback loops and execute customer recovery workflows automatically — represent the industry's answer to the same insight-action gap that Odradek addresses through its FeedbackRule and ActionLog architecture. The convergence between Gartner's market definition and Odradek's architecture confirms that the platform is positioned in a rapidly growing and strategically important market category.

Source: CX Today, "Gartner Magic Quadrant for VoC Platforms 2026," March 13, 2026; CXM World, "Gartner's 2026 VoC Magic Quadrant," March 17, 2026.

### 2.12.2 Forrester: CX Quality at an All-Time Low

Forrester's Customer Experience Index (CX Index) 2025, based on analysis of over 275,000 customers' perceptions of 469 brands across 12 industries and 13 countries, reveals that US and Canadian consumer perceptions of CX quality have dropped for a fourth consecutive year to an all-time low. In the US, 25% of brands evaluated had statistically significant losses while only 7% improved. Contributing factors include "a decreased focus on customer obsession" and "the persistent gap" between what organizations promise and what they deliver — what Forrester characterizes as the gap between insight collection and operational action.

Forrester's separate 2025 State of Feedback Management (VoC) and CX Measurement report (August 2025) is even more directly relevant. Based on a global survey of VoC and CX practitioners, it found that "most programs still struggle with getting stakeholders to act on CX insights and suffer from a lack of stakeholder confidence." The report identifies weaknesses in core practices: collecting feedback, tracking metrics, and effectively analyzing different types of data. This finding directly validates Odradek's H1 hypothesis (the insight-action gap) and H2 hypothesis (signal fragmentation) — the two highest-priority problems the platform addresses.

Source: Forrester, "Customer Experience Quality In The US Falls To An(other) All-Time Low," 2025; Forrester, "Summary: The State Of Feedback Management (VoC) And CX Measurement, 2025," RES185113, August 8, 2025.

### 2.12.3 Qualtrics: "CX Has an Action Problem"

At the Qualtrics X4 Summit (March 2026), the dominant theme was explicitly framed as "CX has an action problem" (CMSWire, March 23, 2026). The conference revealed a decisive industry shift from collecting feedback to acting on it — where "AI, speed, and frontline execution now define CX success." Qualtrics announced new capabilities to "turn customer feedback into actionable outcomes that drive loyalty and growth, positioning itself as more than a survey platform" (Futurum Group, March 20, 2026).

Qualtrics' XM Institute 2025 State of Customer Experience Management study, surveying practitioners from organizations with 1,000+ employees, found that the top obstacles to CX management success include difficulty getting stakeholders to act on insights and connecting CX work to business outcomes. The study assessed CX maturity stages and found that most organizations remain in early stages — collecting data but failing to operationalize it.

Qualtrics' response — launching "AI Agents that close the loop in real time" (CX Today, 2026) — mirrors Odradek's FeedbackRule auto-execution capability. The Qualtrics XM Institute's "four action loops" framework (immediate response, proactive improvement, strategic change, cultural transformation) provides a conceptual model that maps directly to Odradek's multi-level architecture: signal triage, insight-to-action routing, rule-based automation, and organizational learning via AbLearnings.

Source: CMSWire, "Insight Is Cheap. Execution Is Everything. What Qualtrics X4 Made Clear," March 23, 2026; Futurum Group, "Can Qualtrics Help Customers Move From Listening to Insights to Driving Action?," March 20, 2026; CX Today, "Qualtrics Launches AI Agents That Close the Loop in Real Time," 2026; Qualtrics XM Institute, "The State of Customer Experience Management, 2025."

### 2.12.4 Medallia: Closed-Loop Programs Failing to Deliver

Medallia, named a Leader in the Gartner Magic Quadrant for VoC for the fifth consecutive year, published research in August 2025 explicitly titled "Is Your Closed-Loop Feedback Program Falling Flat?" The article identifies a critical disconnect: "Many CX leaders launch closed-loop feedback (CLF) programs with a goal of driving action, only to later discover that their programs aren't delivering the expected insights or impact." Medallia attributes this failure to companies' inability to define clear objectives, track the right data, and connect feedback to operational workflows — findings that directly validate Odradek's unified signal-to-insight-to-action architecture.

Medallia's 2025 CX Trends predictions emphasize that AI will move from analyzing feedback to autonomously triggering actions, that organizations must combine direct feedback (surveys), indirect signals (social media, reviews), and inferred data (behavioral analytics) into unified customer profiles — a capability Medallia calls "Total Experience Profiles." This multi-signal philosophy is precisely what Odradek implements through its 13 signal source types and unified Signal model.

Medallia's 2025 customer loyalty statistics further underscore the urgency: loyalty is declining as customers become less tolerant of gaps between expectation and execution, making real-time closed-loop feedback more critical than ever.

Source: Medallia, "Is Your Closed-Loop Feedback Program Falling Flat? Try This Framework," August 21, 2025; Medallia, "Our Top 8 Predictions for Customer Experience Trends in 2025," December 18, 2024; Medallia, "Top 2025 Customer Loyalty Statistics CX Professionals Need to Know," 2025.

### 2.12.5 Bain & Company: The Economics of Closing the Loop

Bain & Company, the creators of the Net Promoter System, have published extensively on the business case for closed-loop customer feedback. Their research demonstrates that most survey responses "disappear into a black hole" — the fate of most survey responses — with companies failing to acknowledge, analyze, or act on individual customer feedback. Bain's closed-loop model requires that feedback reaches frontline employees who then follow up with individual customers, creating a direct connection between customer voice and organizational response.

Bain documents that companies implementing closed-loop NPS programs achieve significantly higher customer retention and can "turn around a decline in market share" through systematic feedback-to-action processes. The key insight from Bain's work is that the value of customer feedback lies not in the measurement itself but in the operational response it triggers — a principle that is architecturally embedded in Odradek's pipeline from Signal to Insight to Action.

Source: Bain & Company, "Closing the Customer Feedback Loop" (Harvard Business Online, December 2009); Bain & Company, "Closing the Loop — Loyalty Insights #6."

### 2.12.6 Salesforce: Trust Declining, Expectations Rising

Salesforce's "State of the AI Connected Customer" (7th edition), surveying 16,585 consumers and business buyers worldwide, found that customer trust in businesses using AI ethically has dropped from 58% in 2023 to 42%. Despite this trust decline, customer expectations for personalized, connected experiences continue to rise. The report documents that customers expect businesses to act on their feedback faster and more transparently — creating the paradox of increasing expectations amid decreasing trust.

For Odradek, this validates the need for transparent, auditable action workflows (ActionLog with execution status tracking) and human-in-the-loop automation (the pending_approval status in ActionLog), ensuring that automated actions can be reviewed and trusted.

Source: Salesforce, "State of the AI Connected Customer," 7th Edition, 2025.

### 2.12.7 Zendesk: The Cost of Inaction

Zendesk's CX Trends 2026 report, based on global surveys of consumers and CX managers, provides critical statistics: 52% of customers will switch to a competitor after a single negative experience; 85% of CX managers state that customers will stop using brands if problems are not resolved upon first contact; and 81% of CX executives say that easy access to internal knowledge significantly improves decision-making.

The report identifies five trends reshaping CX in 2026: contextual intelligence (AI that understands context, not just keywords), multimodal interactions, transparency and governance, memory-rich AI for personalization, and first-contact resolution. The emphasis on first-contact resolution and contextual intelligence aligns with Odradek's severity-based prioritization and multi-signal context enrichment.

Source: Zendesk, "CX Trends 2026"; Zendesk, "35 Customer Experience Statistics to Know for 2026," updated March 5, 2026; Leafworks, "Zendesk CX Trends 2026," November 2025.

### 2.12.8 Cross-Industry Statistics Summary

The following statistics, drawn from the industry sources above, provide quantitative evidence for the pain points Odradek addresses:

| Statistic | Source |
|-----------|--------|
| CX quality in the US has fallen for 4 consecutive years to an all-time low | Forrester CX Index 2025 |
| 25% of US brands showed statistically significant CX declines; only 7% improved | Forrester CX Index 2025 |
| Most VoC programs struggle with getting stakeholders to act on insights | Forrester State of Feedback Management 2025 |
| Customer trust in ethical AI use dropped from 58% (2023) to 42% | Salesforce State of AI Connected Customer 2025 |
| 52% of customers switch to a competitor after a single negative experience | Zendesk CX Trends 2026 |
| 85% of CX managers say customers leave if problems aren't resolved on first contact | Zendesk CX Trends 2026 |
| 99% of consumers say customer service influences buying decisions | The Futurum Group / Webex 2025 |
| 70% of customers abandon a brand after just two bad experiences | Emplifi / Webex 2025 |
| Gartner predicts AI Experience Agents will autonomously act on customer records | Gartner MQ for VoC 2026 |
| Closed-loop feedback programs often fail to deliver expected insights or impact | Medallia 2025 |
| "CX has an action problem" — the dominant theme at Qualtrics X4 2026 | CMSWire / Qualtrics X4 2026 |

---

## 2.13 Synthesis and Theoretical Positioning

The Odradek platform sits at the intersection of multiple academic disciplines. It draws on Voice of the Customer methodologies (Griffin & Hauser, 1993), sentiment analysis and NLP (Liu, 2012; Devlin et al., 2019), business intelligence frameworks (Ackoff, 1989; Davenport & Harris, 2007), anomaly detection (Chandola et al., 2009), decision support systems (Sprague, 1980; Lee & See, 2004), experimental design (Kohavi et al., 2020), churn prediction (Neslin et al., 2006), data integration (Lenzerini, 2002), information visualization (Few, 2006; Munzner, 2014), business process management (van der Aalst, 2013), and knowledge management (Nonaka & Takeuchi, 1995).

The industry practitioner evidence reviewed in section 2.12 provides powerful corroboration: Forrester's 2025 State of Feedback Management survey found that most VoC programs struggle with getting stakeholders to act on insights; Qualtrics' X4 2026 summit was explicitly themed around the declaration that "CX has an action problem"; Medallia documented that closed-loop feedback programs frequently fail to deliver expected impact; and Gartner's 2026 Magic Quadrant for VoC Platforms identifies autonomous action execution as the defining capability of next-generation platforms. These convergent industry findings — from the world's leading analyst firms and the two largest VoC platform vendors — validate the core problem that Odradek addresses.

The platform's distinctive contribution lies in its integration of these traditionally separate domains into a unified feedback management lifecycle. Where most existing systems address individual components — a survey tool here, a BI dashboard there, a ticketing system elsewhere — Odradek implements the complete signal-to-insight-to-action-to-learning pipeline that both academic literature and industry practice consistently identify as necessary but rarely achieve. This closed-loop architecture directly addresses the feedback-action gap documented by Bone et al. (2017), the insight-action gap identified by Ghasemaghaei et al. (2017), the stakeholder action failure measured by Forrester (2025), and the organizational learning imperatives articulated by Argyris and Schon (1978) and March (1991).

---

## 2.14 Design Science Research as Methodological Foundation

The methodological grounding for this thesis derives from Design Science Research (DSR), a paradigm distinct from both positivist and interpretivist traditions in information systems research. Where behavioural science seeks to develop and verify theories that explain or predict human and organizational phenomena, design science seeks to extend human and organizational capabilities by creating purposeful artifacts (Hevner, March, Park, & Ram, 2004). For a thesis whose central contribution is a working platform (Odradek) intended to address the feedback-action gap documented throughout sections 2.1–2.13, DSR is the appropriate paradigm: it treats the artifact itself as a legitimate research output and requires its evaluation against articulated problem criteria.

Hevner et al. (2004) articulate seven guidelines for rigorous DSR: (1) design as a purposeful artifact; (2) problem relevance to a business need; (3) design evaluation through well-executed methods; (4) clear research contributions; (5) research rigor through grounding in existing foundations; (6) design as an iterative search process; and (7) communication to both technology and management audiences. This thesis is structured to satisfy each guideline — the artifact is the Odradek platform, the problem relevance is grounded in Bone et al. (2017), Forrester (2025), and Qualtrics X4 (2026), evaluation combines qualitative practitioner interviews with quantitative task metrics, contributions span artifact-instantiation and design-principle knowledge, rigor is established by this literature review, and iterative search characterizes the platform's development history.

Peffers, Tuunanen, Rothenberger, and Chatterjee (2007) operationalize DSR through a six-activity Design Science Research Methodology (DSRM) process model: problem identification and motivation; definition of solution objectives; design and development; demonstration; evaluation; and communication. The DSRM provides a nominal process sequence but explicitly supports multiple entry points — problem-centred, objective-centred, design-centred, or observation-centred initiation. This thesis follows a problem-centred initiation (beginning with the documented feedback-action gap) proceeding linearly through the activities.

Hevner (2007) later articulated the Three Cycle View of DSR: the Relevance Cycle connects the research to the application environment (practitioner needs and field-test opportunities); the Rigor Cycle connects the research to the existing knowledge base (theories, methods, prior artifacts); and the Design Cycle iterates between building and evaluating the artifact. Gregor and Hevner (2013) extend this framework by distinguishing levels of DSR contribution: Level 1 (situated implementations), Level 2 (nascent design theory: constructs, models, methods, design principles), and Level 3 (well-developed design theory). The present thesis targets a Level 1 contribution (the Odradek artifact as situated implementation) with a Level 2 component (design principles for feedback-to-action automation derived from the evaluation).

DSR has been widely adopted in information systems thesis research and has developed associated evaluation frameworks. Prat, Comyn-Wattiau, and Akoka (2015) provide a taxonomy of DSR evaluation criteria organized into five dimensions — goal, environment, structure, activity, and evolution — and across evaluation methods including observational, analytical, experimental, testing, and descriptive approaches. This thesis draws on their framework in selecting usefulness, ease of use, efficacy, and organizational fit as primary evaluation constructs, operationalized through semi-structured interviews and the System Usability Scale (Brooke, 1996).

The alignment between DSR and the Odradek thesis is strong on multiple dimensions. First, the research problem is irreducibly design-oriented: the feedback-action gap cannot be closed by observation alone but requires an artifact that changes the practitioner's workflow. Second, the contribution structure is inherently dual — practical (a working platform marketers can use) and theoretical (design principles abstracted from the artifact). Third, DSR's insistence on problem relevance aligns with the industry evidence reviewed in section 2.12, which establishes the gap's practical importance independently of academic framing. DSR thus functions here not as a methodological veneer but as a genuine fit between research question and research paradigm.

---

## 2.15 Responsible AI and Ethical Considerations in Automated Marketing

As an MSc Responsible AI thesis, this work carries an obligation to examine its artifact through an ethical and governance lens that extends beyond functional performance. Automated feedback-to-action systems occupy a space where algorithmic decisions — routing a complaint to a specific team, triggering an outreach email, flagging a customer for retention intervention — have meaningful consequences for both customers and internal stakeholders. Responsible AI scholarship provides the conceptual resources for designing such systems accountably.

The foundational ethical principles for AI systems are now broadly converged in the literature. Floridi et al. (2018) synthesize five principles for ethical AI: beneficence, non-maleficence, autonomy, justice, and explicability, the last being specific to AI (extending the traditional four biomedical principles of Beauchamp and Childress, 2001). Jobin, Ienca, and Vayena (2019) conducted a global analysis of 84 AI ethics guidelines and identified transparency, justice and fairness, non-maleficence, responsibility, and privacy as the most widely shared principles. For a feedback automation platform, these principles translate into concrete design requirements: transparent rule definitions, auditable action logs, user-controllable autonomy boundaries, and privacy-respecting data handling.

Human-in-the-loop (HITL) design is a central Responsible AI consideration for any automation system. Shneiderman (2020) argues for a Human-Centered AI framework that simultaneously maximizes human control and computer automation — rejecting the false dichotomy that they must trade off. For marketing automation, this manifests as the distinction between auto-execute rules (high confidence, low risk) and approval-required rules (material impact on customers or brand). Amershi et al. (2019) articulate eighteen guidelines for human-AI interaction spanning initial system use, during interaction, when the system is wrong, and over time — several of which map directly to the Odradek platform's design (e.g., "make clear what the system can do", "make clear how well the system can do what it can do", "support efficient correction", "notify users about changes").

Explainability requirements for automated decisions are heightened in regulated jurisdictions. The European Union's General Data Protection Regulation (GDPR), particularly Article 22, grants data subjects rights with respect to decisions based solely on automated processing that produce legal or similarly significant effects (European Union, 2016). While most marketing automation decisions fall below this legal threshold, the normative direction is clear: automated decisions affecting individuals should be contestable, reviewable, and explicable. The Odradek platform's ActionLog functions as an explainability mechanism — every automated action records the triggering rule, the input signal, the outcome, and the responsible party for review.

The EU AI Act (Regulation 2024/1689), enacted in 2024, establishes a risk-based regulatory framework for AI systems placed on the EU market. Though the Act's highest obligations target high-risk and prohibited applications (biometric categorization, social scoring, and predictive policing among the latter), its transparency requirements extend more broadly to systems interacting with natural persons or generating content. Marketing feedback automation is unlikely to qualify as high-risk under Annex III, but the Act's emphasis on documentation, traceability, human oversight, and data governance informs best-practice design even for lower-risk applications. Crucially, Article 5 prohibits AI systems that use "subliminal techniques beyond a person's consciousness" or "exploit vulnerabilities" to materially distort behaviour in ways likely to cause harm — a constraint that is relevant to automated outreach and retention tactics, particularly when applied to churn-risk customer segments. The regulatory baseline is, however, still consolidating during this thesis's timeframe: the Commission's Digital Omnibus on AI (political agreement of 7 May 2026, pending formal adoption) deferred the high-risk obligations — Annex III use-case systems from 2 August 2026 to 2 December 2027, and Annex I product-safety systems to 2 August 2028 — moved the Article 50 transparency and AI-generated-content marking obligations to 2 December 2026, added a new prohibition on the generation of non-consensual intimate imagery and CSAM, and extended simplified-documentation relief from SMEs to small mid-cap firms. This evolving timeline reinforces the thesis's design stance of treating governance controls (human oversight, audit trails, transparency) as durable design commitments rather than as compliance triggered by any single deadline.

The literature on algorithmic fairness offers additional design guidance. Mehrabi et al. (2021) survey bias and fairness in machine learning, documenting representation, measurement, aggregation, and evaluation biases that can emerge in classification and ranking systems. For a feedback prioritization system, fairness concerns include whether signals from certain customer segments (by language, geography, verbosity, or channel) receive systematically different triage outcomes. While the Odradek platform uses predominantly rule-based logic rather than opaque machine learning classifiers, the design principle of fairness-by-design — auditing routing distributions across segments — remains applicable.

Trust calibration is the bidirectional counterpart to explainability. Lee and See (2004), foundational in the human factors literature on automation, argue that appropriate trust in automation requires that the system's trustworthiness match the user's trust in it — miscalibration produces either disuse (under-trust) or misuse (over-trust). Glikson and Woolley (2020) synthesize evidence on human trust in artificial intelligence across embodiment and representation modalities. For a feedback automation system, these findings underscore the importance of surfacing confidence estimates, providing mechanisms to override automated decisions, and designing the user interface to convey system capability honestly rather than anthropomorphically.

Data governance constitutes a further Responsible AI pillar. Abraham, Schneider, and vom Brocke (2019) synthesize the data governance literature into a framework covering governance structure, decision domains, and mechanisms. For a platform ingesting customer feedback from 13+ sources, data governance requires explicit policies on data provenance, retention, subject-access-request handling, and third-party-processor arrangements. The GDPR principles of lawfulness, purpose limitation, data minimization, accuracy, storage limitation, integrity, and accountability (Article 5) operationalize these obligations for European deployments.

Finally, Responsible AI scholarship increasingly emphasizes the practitioner and organizational dimensions of ethical AI. Rakova et al. (2021) study how organizations actually adopt Responsible AI practices, finding that structural factors (dedicated roles, escalation paths, measurable incentives) matter more than stated principles. For a platform designed for marketing practitioners, Responsible AI cannot be located solely in the artifact's code — it must also be supported by the artifact's affordances (e.g., configurable autonomy boundaries, clear default settings, accessible audit logs) that enable practitioners to enact responsible practice within their organizational context.

Taken together, the Responsible AI literature situates the Odradek platform within a design space where technical capability must be matched by transparency, contestability, human oversight, fairness-aware routing, and auditable data governance. These considerations inform the platform's architecture (section to be elaborated in Chapter 4), the evaluation criteria (Chapter 5), and the discussion of design principles (Chapter 6).

---

## References

Abraham, R., Schneider, J., & vom Brocke, J. (2019). Data governance: A conceptual framework. *International Journal of Information Management*, 49, 424–438.

Ackoff, R. L. (1989). From data to wisdom. *Journal of Applied Systems Analysis*, 16, 3–9.

Aggarwal, C. C. (2017). *Outlier Analysis* (2nd ed.). Springer.

Ahmad, S., Lavin, A., Purdy, S., & Agha, Z. (2017). Unsupervised real-time anomaly detection for streaming data. *Neurocomputing*, 262, 134–147.

Alavi, M., & Leidner, D. E. (2001). Knowledge management and knowledge management systems. *MIS Quarterly*, 25(1), 107–136.

Alpar, P., & Schulz, M. (2016). Self-service business intelligence. *Business & Information Systems Engineering*, 58(2), 151–155.

Anderson, D. J. (2010). *Kanban: Successful Evolutionary Change for Your Technology Business*. Blue Hole Press.

Anderson, E. W., Fornell, C., & Lehmann, D. R. (1994). Customer satisfaction, market share, and profitability. *Journal of Marketing*, 58(3), 53–66.

Argote, L. (2013). *Organizational Learning* (2nd ed.). Springer.

Argyris, C., & Schon, D. A. (1978). *Organizational Learning: A Theory of Action Perspective*. Addison-Wesley.

Arnott, D., & Pervan, G. (2005). A critical analysis of decision support systems research. *Journal of Information Technology*, 20(2), 67–87.

Ascarza, E. (2018). Retention futility: Targeting high-risk customers might be ineffective. *Journal of Marketing Research*, 55(1), 80–98.

Batini, C., Cappiello, C., Francalanci, C., & Maurino, A. (2009). Methodologies for data quality assessment. *ACM Computing Surveys*, 41(3), 1–52.

Bertsimas, D., & Kallus, N. (2020). From predictive to prescriptive analytics. *Management Science*, 66(3), 1025–1044.

Bifet, A., & Gavalda, R. (2007). Learning from time-changing data with adaptive windowing. *Proceedings of the ACM Symposium on Applied Computing*, 443–448.

Blazevic, V., et al. (2013). Beyond traditional word-of-mouth. *Journal of Service Management*, 24(3), 294–313.

Blei, D. M., Ng, A. Y., & Jordan, M. I. (2003). Latent Dirichlet Allocation. *Journal of Machine Learning Research*, 3, 993–1022.

Bleier, A., & Eisenbeiss, M. (2015). The importance of trust for personalized online advertising. *Journal of Marketing*, 79(6), 34–53.

Bleiholder, J., & Naumann, F. (2008). Data fusion. *ACM Computing Surveys*, 41(1), 1–41.

Bone, S. A., et al. (2017). Mere measurement plus. *Journal of Marketing Research*, 54(1), 156–170.

Borenstein, M., Hedges, L. V., Higgins, J. P., & Rothstein, H. R. (2009). *Introduction to Meta-Analysis*. Wiley.

Boyer, J., & Mili, H. (2011). *Agile Business Rule Development*. Springer.

Breunig, M. M., Kriegel, H. P., Ng, R. T., & Sander, J. (2000). LOF: Identifying density-based local outliers. *Proceedings of the ACM SIGMOD Conference*, 93–104.

Brown, T. B., et al. (2020). Language models are few-shot learners. *Proceedings of NeurIPS*.

Buchanan, B. G., & Shortliffe, E. H. (1984). *Rule-Based Expert Systems: The MYCIN Experiments*. Addison-Wesley.

Card, S. K., Mackinlay, J. D., & Shneiderman, B. (1999). *Readings in Information Visualization*. Morgan Kaufmann.

Carlile, P. R. (2004). Transferring, translating, and transforming. *Organization Science*, 15(5), 555–568.

Chandola, V., Banerjee, A., & Kumar, V. (2009). Anomaly detection: A survey. *ACM Computing Surveys*, 41(3), 1–58.

Chaudhuri, S., Dayal, U., & Narasayya, V. (2011). An overview of business intelligence technology. *Communications of the ACM*, 54(8), 88–98.

Chen, H., Chiang, R. H. L., & Storey, V. C. (2012). Business intelligence and analytics. *MIS Quarterly*, 36(4), 1165–1188.

Christen, P. (2012). *Data Matching*. Springer.

Cleveland, W. S., & McGill, R. (1984). Graphical perception. *Journal of the American Statistical Association*, 79(387), 531–554.

Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences*. Lawrence Erlbaum.

Cronin, J. J., & Taylor, S. A. (1992). Measuring service quality. *Journal of Marketing*, 56(3), 55–68.

Davenport, T. H., & Harris, J. G. (2007). *Competing on Analytics*. Harvard Business School Press.

De Haan, E., Verhoef, P. C., & Wiesel, T. (2015). The predictive ability of different customer feedback metrics. *International Journal of Research in Marketing*, 32(2), 195–206.

Delen, D., & Demirkan, H. (2013). Data, information and analytics as services. *Decision Support Systems*, 55(1), 218–225.

Dellermann, D., Ebel, P., Sollner, M., & Leimeister, J. M. (2019). Hybrid intelligence. *Business & Information Systems Engineering*, 61(5), 637–643.

Deming, W. E. (1986). *Out of the Crisis*. MIT Press.

Deng, A., Xu, Y., Kohavi, R., & Walker, T. (2013). Improving the sensitivity of online controlled experiments. *Proceedings of KDD*.

Devlin, J., Chang, M. W., Lee, K., & Toutanova, K. (2019). BERT: Pre-training of deep bidirectional transformers. *Proceedings of NAACL*.

Devriendt, F., Moldovan, D., & Verbeke, W. (2018). A literature survey on uplift modeling. *Journal of Big Data*, 5(1), 1–29.

Dixon, M., Freeman, K., & Toman, N. (2010). Stop trying to delight your customers. *Harvard Business Review*, 88(7/8), 116–122.

Dong, X. L., & Srivastava, D. (2015). *Big Data Integration*. Morgan & Claypool.

Edmondson, A. C. (1999). Psychological safety and learning behavior in work teams. *Administrative Science Quarterly*, 44(2), 350–383.

Fader, P. S., & Hardie, B. G. S. (2005). A note on deriving the conditional PMF of the BG/NBD model. *Working paper*, Wharton School.

Few, S. (2006). *Information Dashboard Design*. O'Reilly Media.

Fielding, R. T. (2000). *Architectural Styles and the Design of Network-Based Software Architectures*. Doctoral dissertation, UC Irvine.

Forgy, C. L. (1982). Rete: A fast algorithm for pattern matching. *Artificial Intelligence*, 19(1), 17–37.

Fornell, C., Johnson, M. D., Anderson, E. W., Cha, J., & Bryant, B. E. (1996). The American Customer Satisfaction Index. *Journal of Marketing*, 60(4), 7–18.

Gattermann-Itschert, T., & Thonemann, U. W. (2021). How training on multiple time slices improves churn prediction. *European Journal of Operational Research*, 295(2), 664–674.

Ghasemaghaei, M., Hassanein, K., & Turel, O. (2017). Increasing firm agility through the use of data analytics. *International Journal of Information Management*, 37(1), 1–11.

Gorry, G. A., & Scott Morton, M. S. (1971). A framework for management information systems. *Sloan Management Review*, 13(1), 55–70.

Griffin, A., & Hauser, J. R. (1993). The voice of the customer. *Marketing Science*, 12(1), 1–27.

Grootendorst, M. (2022). BERTopic: Neural topic modeling with a class-based TF-IDF procedure. *arXiv preprint arXiv:2203.05794*.

Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). On calibration of modern neural networks. *Proceedings of ICML*.

Gupta, S., et al. (2006). Modeling customer lifetime value. *Journal of Service Research*, 9(2), 139–155.

Harel, D. (1987). Statecharts. *Science of Computer Programming*, 8(3), 231–274.

Harrower, M., & Brewer, C. A. (2003). ColorBrewer.org. *The Cartographic Journal*, 40(1), 27–37.

Heer, J., Bostock, M., & Ogievetsky, V. (2009). A tour through the visualization zoo. *Communications of the ACM*, 53(6), 59–67.

Hohpe, G., & Woolf, B. (2003). *Enterprise Integration Patterns*. Addison-Wesley.

Hollingsworth, D. (1995). *The Workflow Reference Model*. WfMC-TC-1003.

Homburg, C., Jozic, D., & Kuehnl, C. (2017). Customer experience management. *Journal of Marketing*, 81(5), 69–96.

Keiningham, T. L., Cooil, B., Andreassen, T. W., & Aksoy, L. (2007). A longitudinal examination of Net Promoter. *Journal of Marketing*, 71(3), 39–51.

Kimball, R., & Ross, M. (2013). *The Data Warehouse Toolkit* (3rd ed.). Wiley.

Kohavi, R., Longbotham, R., Sommerfield, D., & Henne, R. M. (2009). Controlled experiments on the web. *Data Mining and Knowledge Discovery*, 18(1), 140–181.

Kohavi, R., Tang, D., & Xu, Y. (2020). *Trustworthy Online Controlled Experiments*. Cambridge University Press.

Kumar, A., van der Aalst, W. M. P., & Verbeek, E. M. W. (2002). Dynamic work distribution. *Data & Knowledge Engineering*, 43(3), 317–346.

Kumar, V., Pozza, I. D., & Ganesh, J. (2013). Revisiting the satisfaction-loyalty relationship. *Journal of Retailing*, 89(3), 246–262.

Lariviere, B., & Van den Poel, D. (2005). Predicting customer retention using random forests. *Expert Systems with Applications*, 29(2), 472–484.

LaValle, S., et al. (2011). Big data, analytics and the path from insights to value. *MIT Sloan Management Review*, 52(2), 21–32.

Lee, J. D., & See, K. A. (2004). Trust in automation. *Human Factors*, 46(1), 50–80.

Lemon, K. N., & Verhoef, P. C. (2016). Understanding customer experience throughout the customer journey. *Journal of Marketing*, 80(6), 69–96.

Lenzerini, M. (2002). Data integration: A theoretical perspective. *Proceedings of ACM PODS*, 233–246.

Lepenioti, K., Bousdekis, A., Apostolou, D., & Mentzas, G. (2020). Prescriptive analytics: Literature review. *Journal of Industrial Information Integration*, 19, 100141.

Liu, B. (2012). *Sentiment Analysis and Opinion Mining*. Morgan & Claypool.

Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). Isolation forest. *Proceedings of IEEE ICDM*, 413–422.

Luo, X., & Homburg, C. (2007). Neglected outcomes of customer satisfaction. *Journal of Marketing*, 71(2), 133–149.

March, J. G. (1991). Exploration and exploitation in organizational learning. *Organization Science*, 2(1), 71–87.

Montgomery, D. C. (2019). *Introduction to Statistical Quality Control* (8th ed.). Wiley.

Morgan, N. A., & Rego, L. L. (2006). The value of different customer satisfaction metrics. *Marketing Science*, 25(5), 426–439.

Munzner, T. (2014). *Visualization Analysis and Design*. CRC Press.

Neslin, S. A., et al. (2006). Defection detection. *Journal of Marketing Research*, 43(2), 204–211.

Nonaka, I., & Takeuchi, H. (1995). *The Knowledge-Creating Company*. Oxford University Press.

Pang, B., & Lee, L. (2008). Opinion mining and sentiment analysis. *Foundations and Trends in Information Retrieval*, 2(1–2), 1–135.

Pang, B., Lee, L., & Vaithyanathan, S. (2002). Thumbs up? Sentiment classification using machine learning. *Proceedings of EMNLP*.

Parasuraman, A., Zeithaml, V. A., & Berry, L. L. (1988). SERVQUAL. *Journal of Retailing*, 64(1), 12–40.

Parasuraman, R., Sheridan, T. B., & Wickens, C. D. (2000). A model for types and levels of human interaction with automation. *IEEE Transactions on SMC*, 30(3), 286–297.

Pfeffer, J., & Sutton, R. I. (2006). *Hard Facts, Dangerous Half-Truths, and Total Nonsense*. Harvard Business School Press.

Platt, J. (1999). Probabilistic outputs for support vector machines. *Advances in Large Margin Classifiers*, 61–74.

Polanyi, M. (1966). *The Tacit Dimension*. University of Chicago Press.

Rahm, E., & Bernstein, P. A. (2001). A survey of approaches to automatic schema matching. *The VLDB Journal*, 10(4), 334–350.

Reichheld, F. F. (2003). The one number you need to grow. *Harvard Business Review*, 81(12), 46–54.

Reichert, M., & Weber, B. (2012). *Enabling Flexibility in Process-Aware Information Systems*. Springer.

Ross, R. G. (2003). *Principles of the Business Rule Approach*. Addison-Wesley.

Rowley, J. (2007). The wisdom hierarchy. *Journal of Information Science*, 33(2), 163–180.

Russell, N., van der Aalst, W. M. P., ter Hofstede, A. H. M., & Edmond, D. (2005). Workflow resource patterns. *Information Systems*, 30(3).

Saaty, T. L. (1980). *The Analytic Hierarchy Process*. McGraw-Hill.

Sahay, B. S., & Ranjan, J. (2008). Real-time business intelligence. *Information Management & Computer Security*, 16(1), 28–48.

Sahni, N. S., Wheeler, S. C., & Chintagunta, P. (2018). Personalization in email marketing. *Marketing Science*, 37(2), 236–258.

Sakurada, M., & Yairi, T. (2014). Anomaly detection using autoencoders. *Proceedings of the MLSDA Workshop*, 4–11.

Sarikaya, A., et al. (2019). What do we talk about when we talk about dashboards? *IEEE TVCG*, 25(1), 682–692.

Senge, P. M. (1990). *The Fifth Discipline*. Doubleday.

Shewhart, W. A. (1931). *Economic Control of Quality of Manufactured Product*. Van Nostrand.

Shneiderman, B. (1996). The eyes have it. *Proceedings of the IEEE Symposium on Visual Languages*, 336–343.

Shortliffe, E. H. (1976). *Computer-Based Medical Consultations: MYCIN*. Elsevier.

Sprague, R. H. (1980). A framework for the development of decision support systems. *MIS Quarterly*, 4(4), 1–26.

Sterman, J. D. (2000). *Business Dynamics*. Irwin/McGraw-Hill.

Sweller, J. (1988). Cognitive load during problem solving. *Cognitive Science*, 12(2), 257–285.

Syed, R., et al. (2020). Robotic process automation: Contemporary themes and challenges. *Computers in Industry*, 115, 103162.

Taboada, M., et al. (2011). Lexicon-based methods for sentiment analysis. *Computational Linguistics*, 37(2), 267–307.

Taylor, S. J., & Letham, B. (2018). Forecasting at scale. *The American Statistician*, 72(1), 37–45.

Thomke, S. (2003). *Experimentation Matters*. Harvard Business School Press.

Tirunillai, S., & Tellis, G. J. (2014). Mining marketing meaning from online chatter. *Journal of Marketing Research*, 51(4), 463–479.

Tufte, E. R. (2001). *The Visual Display of Quantitative Information* (2nd ed.). Graphics Press.

van der Aalst, W. M. P. (2013). Business process management: A comprehensive survey. *ISRN Software Engineering*, 2013, 1–37.

van der Aalst, W. M. P. (2016). *Process Mining: Data Science in Action* (2nd ed.). Springer.

van der Aalst, W. M. P., ter Hofstede, A. H. M., Kiepuszewski, B., & Barros, A. P. (2003). Workflow patterns. *Distributed and Parallel Databases*, 14(1), 5–51.

van der Aalst, W. M. P., Bichler, M., & Heinzl, A. (2018). Robotic process automation. *Business & Information Systems Engineering*, 60(4), 269–272.

Vaswani, A., et al. (2017). Attention is all you need. *Proceedings of NeurIPS*.

Verbeke, W., et al. (2012). New insights into churn prediction. *European Journal of Operational Research*, 218(1), 211–229.

Verhoef, P. C., Kannan, P. K., & Inman, J. J. (2015). From multi-channel retailing to omni-channel retailing. *Journal of Retailing*, 91(2), 174–181.

Wang, Y., Huang, M., Zhu, X., & Zhao, L. (2016). Attention-based LSTM for aspect-level sentiment classification. *Proceedings of EMNLP*.

Ware, C. (2012). *Information Visualization* (3rd ed.). Morgan Kaufmann.

Wedel, M., & Kannan, P. K. (2016). Marketing analytics for data-rich environments. *Journal of Marketing*, 80(6), 97–121.

Wilson, T., Wiebe, J., & Hoffmann, P. (2005). Recognizing contextual polarity. *Proceedings of HLT-EMNLP*.

Wirtz, J., Tambyah, S. K., & Mattila, A. S. (2010). Organizational learning from customer feedback. *Journal of Service Research*.

Woolley, A. W., et al. (2010). Evidence for a collective intelligence factor. *Science*, 330(6004), 686–688.
