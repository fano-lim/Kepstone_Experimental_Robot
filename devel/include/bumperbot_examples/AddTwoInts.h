// Generated by gencpp from file bumperbot_examples/AddTwoInts.msg
// DO NOT EDIT!


#ifndef BUMPERBOT_EXAMPLES_MESSAGE_ADDTWOINTS_H
#define BUMPERBOT_EXAMPLES_MESSAGE_ADDTWOINTS_H

#include <ros/service_traits.h>


#include <bumperbot_examples/AddTwoIntsRequest.h>
#include <bumperbot_examples/AddTwoIntsResponse.h>


namespace bumperbot_examples
{

struct AddTwoInts
{

typedef AddTwoIntsRequest Request;
typedef AddTwoIntsResponse Response;
Request request;
Response response;

typedef Request RequestType;
typedef Response ResponseType;

}; // struct AddTwoInts
} // namespace bumperbot_examples


namespace ros
{
namespace service_traits
{


template<>
struct MD5Sum< ::bumperbot_examples::AddTwoInts > {
  static const char* value()
  {
    return "6a2e34150c00229791cc89ff309fff21";
  }

  static const char* value(const ::bumperbot_examples::AddTwoInts&) { return value(); }
};

template<>
struct DataType< ::bumperbot_examples::AddTwoInts > {
  static const char* value()
  {
    return "bumperbot_examples/AddTwoInts";
  }

  static const char* value(const ::bumperbot_examples::AddTwoInts&) { return value(); }
};


// service_traits::MD5Sum< ::bumperbot_examples::AddTwoIntsRequest> should match
// service_traits::MD5Sum< ::bumperbot_examples::AddTwoInts >
template<>
struct MD5Sum< ::bumperbot_examples::AddTwoIntsRequest>
{
  static const char* value()
  {
    return MD5Sum< ::bumperbot_examples::AddTwoInts >::value();
  }
  static const char* value(const ::bumperbot_examples::AddTwoIntsRequest&)
  {
    return value();
  }
};

// service_traits::DataType< ::bumperbot_examples::AddTwoIntsRequest> should match
// service_traits::DataType< ::bumperbot_examples::AddTwoInts >
template<>
struct DataType< ::bumperbot_examples::AddTwoIntsRequest>
{
  static const char* value()
  {
    return DataType< ::bumperbot_examples::AddTwoInts >::value();
  }
  static const char* value(const ::bumperbot_examples::AddTwoIntsRequest&)
  {
    return value();
  }
};

// service_traits::MD5Sum< ::bumperbot_examples::AddTwoIntsResponse> should match
// service_traits::MD5Sum< ::bumperbot_examples::AddTwoInts >
template<>
struct MD5Sum< ::bumperbot_examples::AddTwoIntsResponse>
{
  static const char* value()
  {
    return MD5Sum< ::bumperbot_examples::AddTwoInts >::value();
  }
  static const char* value(const ::bumperbot_examples::AddTwoIntsResponse&)
  {
    return value();
  }
};

// service_traits::DataType< ::bumperbot_examples::AddTwoIntsResponse> should match
// service_traits::DataType< ::bumperbot_examples::AddTwoInts >
template<>
struct DataType< ::bumperbot_examples::AddTwoIntsResponse>
{
  static const char* value()
  {
    return DataType< ::bumperbot_examples::AddTwoInts >::value();
  }
  static const char* value(const ::bumperbot_examples::AddTwoIntsResponse&)
  {
    return value();
  }
};

} // namespace service_traits
} // namespace ros

#endif // BUMPERBOT_EXAMPLES_MESSAGE_ADDTWOINTS_H