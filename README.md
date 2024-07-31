####System Design
All in one RAG system
A RAG system consists of several parts, in general there are following minimal parts:

documents extracter:

This part is to ingest documents from either local harddrives or search results from internet. It will extract data from different formats' original documents, segment the data into chunks which can be indexed by the document indexer.

document indexer:

This part is to use the vector database and/or traditional search engine to index the data extracted by documents extracter. Then it will provide services to search indexed documents according user input query.

Retreival Augmented Q/A generator:

This part is responsible for generating retrieval-augmented question and answer pairs based on the document found by document indexer. It ususally utilize LLM to generate reasonable answer.

System design
Even the minimal RAG system involves several sub-systems and these systems may interact with each other. In order to increase the development flexibility and flat the development curve, a queue based RAG system is designed below:


Every component must be pluggable and easy to scale. Which means RPC shouldn't be hard-wired means like TCP/InProc/InterProcess, etc.

The best design pattern is a pub-sub model that every component connects to a broker(or proxy) to send requests and receive responses. Generally heavy weight message queue like RabbitMQ, RocketMQ is used to ensure efficiency and reliability. However a Message Queue service is still another monster to administrate and maintain.

Here the new design is to use a broker free queue library ZeroMQ alt text as a queue service.

Thanks to ZeroMQ's reliable and high performence implementation, this framework can scale from single resource restricted node to multinodes huge system.

The new design looks like:


Details of implementation
The following part will describe the implementation which will update in the future since more features will be added. However the basic design will keep the same.

Service starter
The service starter(src/services/service_starter.py) is the entry to start all backend services. This script will use a yaml configuration file. By default it's using resouces/service.yml.

Currently three services are implemented:


Examples
You may find examples from src/clients/index_client.py's main entry.

External dependancies
This project is built on top of ZeroMQ as RPC and MsgPack as serialization protocal.

Implement new service
You only need to implement ServiceWorker in src/services/helpers.py.

The src/services/service_starter_new.py is the main entry and resources/services_new.yml is the configuration. It's pretty straight forward to add/modify any service.

If there is a Init-Once method like src/services/index_service.py to start a chroma db, you only need to implement a method init_once(config) function.
