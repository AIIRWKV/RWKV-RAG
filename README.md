# All in one RAG system

A RAG system consists of several parts, in general there are following minimal parts:
 
 - documents extracter:
 
    This part is to ingest documents from either local harddrives or search results from internet. It will extract data from different formats' original documents, segment the data into chunks which can be indexed by the document indexer.

 - document indexer:

    This part is to use the vector database and/or traditional search engine to index the data extracted by documents extracter. Then it will provide services to search indexed documents according user input query.

 - Retreival Augmented Q/A generator:

    This part is responsible for generating retrieval-augmented question and answer pairs based on the document found by document indexer. It ususally utilize LLM to generate reasonable answer.

# System design

Even the minimal RAG system involves several sub-systems and these systems may interact with each other. In order to increase the development flexibility and flat the development curve, a queue based RAG system is designed below:

```mermaid
sequenceDiagram 
    box indexer
        actor DocumentProvidor
        participant DocumentExtractor
        participant DocumentIndexer
    end
    box query
        actor EndUser
        participant RAGGenerator
    end
    
    DocumentProvidor->>DocumentExtractor: 1.0 Extract contents from documents
    DocumentExtractor->>DocumentIndexer:1.1 Index contents and store them
    EndUser->>DocumentIndexer: 2.0 Find the most relevant document from indexed documents
    activate DocumentIndexer
    DocumentIndexer->>EndUser: 2.1 return the most relevant document from indexed documents
    deactivate DocumentIndexer
    EndUser->>RAGGenerator: 2.2 Generate answer acording the provided document and query
    activate RAGGenerator
    RAGGenerator->>EndUser: 2.3 Return generated answer
    deactivate RAGGenerator
```

Every component must be pluggable and easy to scale. Which means RPC shouldn't be hard-wired means like TCP/InProc/InterProcess, etc.

The best design pattern is a pub-sub model that every component connects to a broker(or proxy) to send requests and receive responses. Generally heavy weight message queue like RabbitMQ, RocketMQ is used to ensure efficiency and reliability. However a Message Queue service is still another monster to administrate and maintain. 

Here the new design is to use a broker free queue library ZeroMQ ![alt text](https://zeromq.org/images/logo.gif) as a queue service. 

Thanks to ZeroMQ's reliable and high performence implementation, this framework can scale from single resource restricted node to multinodes huge system.

The new design looks like:
```mermaid
stateDiagram-v2
    Client
    state Client{
        Clients1
        Clients2
        Clients3
        Clients...
    }
    note left of Client
        Clients only need to talk to the Proxy's FrontEnd. 
        The Router of the Proxy will send the requests to one of the service instance through Backend.
         Clients don't need to worry about the status of service cluster nor which server is anwsering specific request.
    end note
    state ProxyZeroMQ {
        FrontEnd --> Router
        Router --> FrontEnd
        Router --> BackEnd
        BackEnd --> Router
    }
    note right of ProxyZeroMQ
        This is provided by ZeroMQ as a library 
        which eliminates the maintainance of a separate service.
        Moreover ZeroMQ's performance is much higher than all alternatives and 
        still provides very good scalability when the application gets massive.
    end note
    Client --> FrontEnd
    FrontEnd --> Client
    BackendService --> BackEnd
    BackEnd --> BackendService
    state BackendService{
        Service1
        Service2
        Service3
        Service...
    }
    note right of BackendService
        Service subscribe messages from Proxy and the instances 
        can be scaled up and down according the load. 
    end note
```

# Details of implementation

The following part will describe the implementation which will update in the future since more features will be added. However the basic design will keep the same.

## Service starter

The service starter(src/services/service_starter.py) is the entry to start all backend services. This script will use a yaml configuration file. By default it's using resouces/service.yml. 

Currently three services are implemented:

```mermaid
stateDiagram-v2

LLM_Client --> LLMFrontEnd
LLMFrontEnd --> LLM_Client
LLM_Proxy
state LLM_Proxy{
    LLMFrontEnd --> LLMRouter 
    LLMRouter --> LLMBackEnd
    LLMRouter --> LLMFrontEnd
    LLMBackEnd --> LLMRouter
}
LLMBackEnd --> LLM_Service
LLM_Service --> LLMBackEnd
note right of LLM_Service
    There are 3 services provided by LLM Service:
    . GetEmbeddings to return paragraph's embeddings
    . Cross Encoder Score, rerank the query/paragraph
    . generate_text generate text according contexts.

    All three models share the same RWKV_V6 base model 
    with different Lora to provide different functions.
end note

CacheClient
Cache_Proxy
state Cache_Proxy{
    CacheFrontEnd
    state CacheFrontEnd{
        CacheReaderFrontEnd
        CacheWriterFrontEnd
    }
    CacheFrontEnd --> CacheRouter 
    CacheRouter -->  CacheFrontEnd
    CacheRouter --> CacheBackend
    CacheBackend
    state CacheBackend{
        CacheReaderBackend
        CacheWriterBackend
    }
}
CacheClient --> CacheFrontEnd
CacheFrontEnd --> CacheClient
CacheService --> CacheBackend
CacheBackend --> CacheService
note right of CacheService
CacheService utilizes SQLite as local cache.
So there are several readers and only one writer process.
end note


IndexClient
IndexProxy
state IndexProxy{
    IndexFrontEnd --> IndexRouter
    IndexRouter --> IndexFrontEnd
    IndexRouter --> IndexBackend
    IndexBackend --> IndexRouter
}
IndexClient --> IndexFrontEnd
IndexFrontEnd --> IndexClient
IndexBackend --> IndexService
IndexService --> IndexBackend
IndexService --> LLM_Client :Call when indexing documents
IndexService --> ChromaDB :ChromaDB is used to store vectors and search vectors
note right of IndexService
IndexService provide two functions:
. Index the texts. In this function, Index Service will call LLM_Client to get embeddings and store them into chromaDB
. Search documents according query.
end note

```


